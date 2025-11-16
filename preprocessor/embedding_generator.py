import json
import logging
from pathlib import Path
from typing import (
    Dict,
    List,
    Optional,
)

from PIL import Image
import cv2
import numpy as np
from rich.console import Console
from rich.progress import Progress
import torch
import torchvision.transforms.functional as TF
from transformers import (
    AutoModel,
    AutoProcessor,
)

from preprocessor.utils.error_handling_logger import ErrorHandlingLogger

console = Console()


class EmbeddingGenerator:
    DEFAULT_MODEL = "Alibaba-NLP/gme-Qwen2-VL-7B-Instruct"
    DEFAULT_OUTPUT_DIR = Path("embeddings")
    DEFAULT_SEGMENTS_PER_EMBEDDING = 5
    DEFAULT_KEYFRAME_STRATEGY = "scene_changes"
    OPTIMAL_IMAGE_SIZE = (1335, 751)
    MAX_PIXEL_BUDGET = 1003520

    def __init__(self, args: Dict):
        self.transcription_jsons: Path = args["transcription_jsons"]
        self.videos: Optional[Path] = args.get("videos")
        self.output_dir: Path = args.get("output_dir", self.DEFAULT_OUTPUT_DIR)
        self.model_name: str = args.get("model", self.DEFAULT_MODEL)
        self.segments_per_embedding: int = args.get("segments_per_embedding", self.DEFAULT_SEGMENTS_PER_EMBEDDING)
        self.keyframe_strategy: str = args.get("keyframe_strategy", self.DEFAULT_KEYFRAME_STRATEGY)
        self.generate_text: bool = args.get("generate_text", True)
        self.generate_video: bool = args.get("generate_video", True)
        self.device: str = args.get("device", "cuda" if torch.cuda.is_available() else "cpu")
        self.scene_timestamps_dir: Optional[Path] = args.get("scene_timestamps_dir")

        self.logger: ErrorHandlingLogger = ErrorHandlingLogger(
            class_name=self.__class__.__name__,
            loglevel=logging.DEBUG,
            error_exit_code=9,
        )

        self.model = None
        self.processor = None

    def work(self) -> int:
        try:
            self._exec()
        except Exception as e:
            self.logger.error(f"Embedding generation failed: {e}")
        return self.logger.finalize()

    def _exec(self) -> None:
        console.print(f"[cyan]Loading model: {self.model_name}[/cyan]")
        console.print(f"[cyan]Device: {self.device}[/cyan]")

        self._load_model()

        transcription_files = list(self.transcription_jsons.glob("**/*.json"))
        if not transcription_files:
            console.print("[yellow]No transcription files found[/yellow]")
            return

        console.print(f"[blue]Processing {len(transcription_files)} transcriptions...[/blue]")

        with Progress() as progress:
            task = progress.add_task("[cyan]Generating embeddings...", total=len(transcription_files))

            for trans_file in transcription_files:
                try:
                    self._process_transcription(trans_file)
                except Exception as e:
                    self.logger.error(f"Failed to process {trans_file}: {e}")
                finally:
                    progress.advance(task)

        console.print("[green]Embedding generation completed[/green]")

    def _load_model(self) -> None:
        try:
            self.processor = AutoProcessor.from_pretrained(self.model_name, trust_remote_code=True)
            self.model = AutoModel.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                device_map=self.device,
                trust_remote_code=True,
            )
            console.print("[green]Model loaded successfully[/green]")

        except Exception as e:
            self.logger.error(f"Failed to load model: {e}")
            raise

    def _process_transcription(self, trans_file: Path) -> None:
        with open(trans_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        console.print(f"[cyan]Processing: {trans_file.name}[/cyan]")

        text_embeddings = []
        video_embeddings = []

        if self.generate_text:
            text_embeddings = self._generate_text_embeddings(data)

        if self.generate_video and self.videos:
            video_path = self._get_video_path(trans_file, data)
            if video_path and video_path.exists():
                video_embeddings = self._generate_video_embeddings(video_path, data)

        data["text_embeddings"] = text_embeddings
        data["video_embeddings"] = video_embeddings

        with open(trans_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        console.print(
            f"[green]{trans_file.name}: {len(text_embeddings)} text, {len(video_embeddings)} video embeddings[/green]",
        )

    def _generate_text_embeddings(self, data: Dict) -> List[Dict]:
        segments = data.get("segments", [])
        if not segments:
            return []

        embeddings = []
        for i in range(0, len(segments), self.segments_per_embedding):
            chunk = segments[i : i + self.segments_per_embedding]
            combined_text = " ".join([seg.get("text", "") for seg in chunk])

            if not combined_text.strip():
                continue

            try:
                embedding = self._encode_text(combined_text)
                embeddings.append(
                    {
                        "segment_range": [chunk[0].get("id", i), chunk[-1].get("id", i + len(chunk) - 1)],
                        "text": combined_text,
                        "embedding": embedding.tolist(),
                    },
                )
            except Exception as e:
                self.logger.error(f"Failed to generate text embedding for segments {i}-{i+len(chunk)}: {e}")

        return embeddings

    def _generate_video_embeddings(self, video_path: Path, data: Dict) -> List[Dict]:
        if self.keyframe_strategy == "scene_changes":
            return self._generate_from_scenes(video_path, data)
        if self.keyframe_strategy == "keyframes":
            return self._generate_from_keyframes(video_path)
        if self.keyframe_strategy == "color_diff":
            return self._generate_from_color_diff(video_path)
        self.logger.error(f"Unknown keyframe strategy: {self.keyframe_strategy}")
        return []

    def _generate_from_scenes(self, video_path: Path, data: Dict) -> List[Dict]:
        scene_timestamps = data.get("scene_timestamps", {})
        scenes = scene_timestamps.get("scenes", [])

        if not scenes:
            console.print("[yellow]No scene timestamps found, using keyframes instead[/yellow]")
            return self._generate_from_keyframes(video_path)

        embeddings = []
        cap = cv2.VideoCapture(str(video_path))

        for scene in scenes:
            start_frame = scene.get("start", {}).get("frame", 0)
            mid_frame = start_frame + (scene.get("frame_count", 1) // 2)

            cap.set(cv2.CAP_PROP_POS_FRAMES, mid_frame)
            ret, frame = cap.read()

            if not ret:
                continue

            try:
                embedding = self._encode_frame(frame)
                fps = scene_timestamps.get("video_info", {}).get("fps", 30)
                embeddings.append(
                    {
                        "frame_number": int(mid_frame),
                        "timestamp": float(mid_frame / fps),
                        "type": "scene_mid",
                        "embedding": embedding.tolist(),
                    },
                )
            except Exception as e:
                self.logger.error(f"Failed to generate video embedding for frame {mid_frame}: {e}")

        cap.release()
        return embeddings

    def _generate_from_keyframes(self, video_path: Path) -> List[Dict]:
        embeddings = []
        cap = cv2.VideoCapture(str(video_path))
        fps = cap.get(cv2.CAP_PROP_FPS)

        frame_num = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_num % int(fps * 5) == 0:
                try:
                    embedding = self._encode_frame(frame)
                    embeddings.append(
                        {
                            "frame_number": int(frame_num),
                            "timestamp": float(frame_num / fps),
                            "type": "keyframe",
                            "embedding": embedding.tolist(),
                        },
                    )
                except Exception as e:
                    self.logger.error(f"Failed to generate video embedding for frame {frame_num}: {e}")

            frame_num += 1

        cap.release()
        return embeddings

    def _generate_from_color_diff(self, video_path: Path) -> List[Dict]:
        embeddings = []
        cap = cv2.VideoCapture(str(video_path))
        fps = cap.get(cv2.CAP_PROP_FPS)

        prev_hist = None
        frame_num = 0
        threshold = 0.3

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_num % 5 != 0:
                frame_num += 1
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
            hist = cv2.normalize(hist, hist).flatten()

            if prev_hist is not None:
                diff = np.sum(np.abs(hist - prev_hist))
                if diff > threshold:
                    try:
                        embedding = self._encode_frame(frame)
                        embeddings.append(
                            {
                                "frame_number": int(frame_num),
                                "timestamp": float(frame_num / fps),
                                "type": "color_change",
                                "embedding": embedding.tolist(),
                            },
                        )
                    except Exception as e:
                        self.logger.error(f"Failed to generate video embedding for frame {frame_num}: {e}")

            prev_hist = hist
            frame_num += 1

        cap.release()
        return embeddings

    def _encode_text(self, text: str) -> np.ndarray:
        inputs = self.processor(text=text, return_tensors="pt", padding=True, truncation=True)
        if self.device == "cuda":
            inputs = {k: v.cuda() for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model(**inputs)
            if isinstance(outputs, torch.Tensor):
                if outputs.dim() == 2:
                    embedding = outputs[0].cpu().numpy()
                elif outputs.dim() == 3:
                    embedding = outputs[:, 0, :].cpu().numpy()[0]
                else:
                    embedding = outputs.cpu().numpy().reshape(-1)
            elif hasattr(outputs, 'pooler_output') and outputs.pooler_output is not None:
                embedding = outputs.pooler_output.cpu().numpy()[0]
            elif hasattr(outputs, 'last_hidden_state'):
                last_hidden = outputs.last_hidden_state
                if last_hidden.dim() == 2:
                    embedding = last_hidden[0].cpu().numpy()
                else:
                    embedding = last_hidden[:, 0, :].cpu().numpy()[0]
            else:
                embedding = outputs.cpu().numpy().reshape(-1)

        return embedding

    def _encode_frame(self, frame: np.ndarray) -> np.ndarray:
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        current_pixels = frame_rgb.shape[0] * frame_rgb.shape[1]
        if current_pixels > self.MAX_PIXEL_BUDGET and self.device == "cuda":
            frame_tensor = torch.from_numpy(frame_rgb).permute(2, 0, 1).unsqueeze(0).float().cuda()
            frame_tensor = TF.resize(frame_tensor, list(reversed(self.OPTIMAL_IMAGE_SIZE)), antialias=True)
            frame_tensor = frame_tensor.squeeze(0).permute(1, 2, 0).byte().cpu().numpy()
            pil_image = Image.fromarray(frame_tensor)
        else:
            pil_image = Image.fromarray(frame_rgb)
            if current_pixels > self.MAX_PIXEL_BUDGET:
                pil_image = pil_image.resize(self.OPTIMAL_IMAGE_SIZE, Image.Resampling.LANCZOS)

        inputs = self.processor(images=pil_image, return_tensors="pt")
        if self.device == "cuda":
            inputs = {k: v.cuda() for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model(**inputs)
            if isinstance(outputs, torch.Tensor):
                if outputs.dim() == 2:
                    embedding = outputs[0].cpu().numpy()
                elif outputs.dim() == 3:
                    embedding = outputs[:, 0, :].cpu().numpy()[0]
                else:
                    embedding = outputs.cpu().numpy().reshape(-1)
            elif hasattr(outputs, 'pooler_output') and outputs.pooler_output is not None:
                embedding = outputs.pooler_output.cpu().numpy()[0]
            elif hasattr(outputs, 'last_hidden_state'):
                last_hidden = outputs.last_hidden_state
                if last_hidden.dim() == 2:
                    embedding = last_hidden[0].cpu().numpy()
                else:
                    embedding = last_hidden[:, 0, :].cpu().numpy()[0]
            else:
                embedding = outputs.cpu().numpy().reshape(-1)

        return embedding

    def _get_video_path(self, trans_file: Path, data: Dict) -> Optional[Path]:
        if not self.videos:
            return None

        episode_info = data.get("episode_info", {})
        season = episode_info.get("season")
        episode = episode_info.get("episode_number")

        if season is None or episode is None:
            return None

        series_name = trans_file.parent.parent.name.lower()
        video_name = f"{series_name}_S{season:02d}E{episode:02d}.mp4"

        if self.videos.is_file():
            return self.videos

        video_path = self.videos / f"Sezon {season}" / video_name
        if not video_path.exists():
            video_path = self.videos / video_name

        return video_path if video_path.exists() else None
