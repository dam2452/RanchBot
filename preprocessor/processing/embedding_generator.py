from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed,
)
import gc
import json
import logging
from pathlib import Path
import re
import traceback
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from PIL import Image
import decord
import numpy as np
from rich.progress import Progress
import torch
from transformers import (
    AutoModel,
    AutoProcessor,
)

from preprocessor.config.config import settings
from preprocessor.utils.console import console
from preprocessor.utils.error_handling_logger import ErrorHandlingLogger
from preprocessor.utils.video_utils import iterate_frames_with_histogram

decord.bridge.set_bridge('torch')


# pylint: disable=too-many-instance-attributes
class EmbeddingGenerator:
    def __init__(self, args: Dict[str, Any]):
        self.transcription_jsons: Path = args["transcription_jsons"]
        self.videos: Optional[Path] = args.get("videos")
        self.output_dir: Path = args.get("output_dir", settings.embedding_default_output_dir)
        self.model_name: str = args.get("model", settings.embedding_model_name)
        self.segments_per_embedding: int = args.get("segments_per_embedding", settings.embedding_segments_per_embedding)
        self.keyframe_strategy: str = args.get("keyframe_strategy", settings.embedding_keyframe_strategy)
        self.keyframe_interval: int = args.get("keyframe_interval", settings.embedding_keyframe_interval)
        self.frames_per_scene: int = args.get("frames_per_scene", settings.embedding_frames_per_scene)
        self.generate_text: bool = args.get("generate_text", True)
        self.generate_video: bool = args.get("generate_video", True)
        self.max_workers: int = args.get("max_workers", settings.embedding_max_workers)
        self.batch_size: int = args.get("batch_size", settings.embedding_batch_size)
        self.device: str = "cuda"
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is not available. This application requires GPU.")
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
            self.__exec()
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error(f"Embedding generation failed: {e}")
        return self.logger.finalize()

    def __exec(self) -> None:
        console.print(f"[cyan]Loading model: {self.model_name}[/cyan]")
        console.print(f"[cyan]Device: {self.device}[/cyan]")
        console.print(f"[cyan]Parallel workers: {self.max_workers}[/cyan]")
        console.print(f"[cyan]Batch size: {self.batch_size}[/cyan]")
        console.print(f"[yellow]DEBUG: self.videos={self.videos}, self.generate_video={self.generate_video}[/yellow]")

        self.__load_model()

        transcription_files = list(self.transcription_jsons.glob("**/*.json"))
        if not transcription_files:
            console.print("[yellow]No transcription files found[/yellow]")
            return

        console.print(f"[blue]Processing {len(transcription_files)} transcriptions...[/blue]")

        if self.max_workers == 1:
            self.__process_sequential(transcription_files)
        else:
            self.__process_parallel(transcription_files)

        console.print("[green]Embedding generation completed[/green]")

    def __process_sequential(self, transcription_files: List[Path]) -> None:
        with Progress() as progress:
            task = progress.add_task("[cyan]Generating embeddings...", total=len(transcription_files))

            for trans_file in transcription_files:
                try:
                    self.__process_transcription(trans_file)
                except Exception as e:  # pylint: disable=broad-exception-caught
                    self.logger.error(f"Failed to process {trans_file}: {e}")
                finally:
                    progress.advance(task)

    def __process_parallel(self, transcription_files: List[Path]) -> None:
        with Progress() as progress:
            task = progress.add_task("[cyan]Generating embeddings...", total=len(transcription_files))

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {executor.submit(self.__process_transcription, f): f for f in transcription_files}

                for future in as_completed(futures):
                    trans_file = futures[future]
                    try:
                        future.result()
                    except Exception as e:  # pylint: disable=broad-exception-caught
                        self.logger.error(f"Failed to process {trans_file}: {e}")
                    finally:
                        progress.advance(task)

    def __load_model(self) -> None:
        try:
            self.processor = AutoProcessor.from_pretrained(self.model_name, trust_remote_code=True)
            self.model = AutoModel.from_pretrained(
                self.model_name,
                torch_dtype="float16",
                device_map="cuda",
                trust_remote_code=True,
            )
            self.model.eval()
            console.print("[green]Model loaded successfully[/green]")

        except Exception as e:
            self.logger.error(f"Failed to load model: {e}")
            raise

    def __process_transcription(self, trans_file: Path) -> None:
        with open(trans_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        has_text_embeddings = "text_embeddings" in data and data["text_embeddings"]
        has_video_embeddings = "video_embeddings" in data and data["video_embeddings"]

        skip_text = self.generate_text and has_text_embeddings
        skip_video = self.generate_video and has_video_embeddings

        if skip_text and skip_video:
            console.print(f"[yellow]Skipping (embeddings already exist): {trans_file.name}[/yellow]")
            return

        if skip_text:
            console.print(f"[yellow]{trans_file.name}: text embeddings already exist, skipping text generation[/yellow]")

        if skip_video:
            console.print(f"[yellow]{trans_file.name}: video embeddings already exist, skipping video generation[/yellow]")

        console.print(f"[cyan]Processing: {trans_file.name}[/cyan]")

        text_embeddings = []
        video_embeddings = []

        if self.generate_text and not skip_text:
            text_embeddings = self.__generate_text_embeddings(data)
        elif has_text_embeddings:
            text_embeddings = data["text_embeddings"]

        if self.generate_video and self.videos and not skip_video:
            video_path = self.__get_video_path(data)
            debug_videos = f"Debug: self.videos={self.videos}, self.generate_video={self.generate_video}"
            console.print(f"[yellow]{debug_videos}[/yellow]")
            debug_video_path = f"Debug: video_path={video_path}, exists={video_path.exists() if video_path else 'N/A (None)'}"
            console.print(f"[yellow]{debug_video_path}[/yellow]")
            if video_path and video_path.exists():
                console.print("[green]Debug: Video found! Processing video embeddings...[/green]")
                if self.scene_timestamps_dir and "scene_timestamps" not in data:
                    scene_data = self.__load_scene_timestamps(video_path)
                    if scene_data:
                        debug_scenes = f"Debug: Loaded scene_data with {len(scene_data.get('scenes', []))} scenes"
                    else:
                        debug_scenes = "Debug: No scene_data loaded"
                    console.print(f"[yellow]{debug_scenes}[/yellow]")
                    if scene_data:
                        data["scene_timestamps"] = scene_data
                video_embeddings = self.__generate_video_embeddings(video_path, data)
            else:
                console.print("[red]Debug: Video not found or video_path is None[/red]")
        elif has_video_embeddings:
            video_embeddings = data["video_embeddings"]

        data["text_embeddings"] = text_embeddings
        data["video_embeddings"] = video_embeddings

        with open(trans_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        console.print(
            f"[green]{trans_file.name}: {len(text_embeddings)} text, {len(video_embeddings)} video embeddings[/green]",
        )

    def __generate_text_embeddings(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
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
                embedding = self.__encode_text(combined_text)
                embeddings.append(
                    {
                        "segment_range": [chunk[0].get("id", i), chunk[-1].get("id", i + len(chunk) - 1)],
                        "text": combined_text,
                        "embedding": embedding.tolist(),
                    },
                )
            except (RuntimeError, ValueError, OSError) as e:
                self.logger.error(f"Failed to generate text embedding for segments {i}-{i+len(chunk)}: {e}")

        return embeddings

    def __generate_video_embeddings(self, video_path: Path, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        if self.keyframe_strategy == "scene_changes":
            return self.__generate_from_scenes(video_path, data)
        if self.keyframe_strategy == "keyframes":
            return self.__generate_from_keyframes(video_path)
        if self.keyframe_strategy == "color_diff":
            return self.__generate_from_color_diff(video_path)
        self.logger.error(f"Unknown keyframe strategy: {self.keyframe_strategy}")
        return []

    def __load_scene_timestamps(self, video_path: Path) -> Optional[Dict[str, Any]]:
        if not self.scene_timestamps_dir or not self.scene_timestamps_dir.exists():
            return None

        video_name = video_path.stem
        episode_match = re.search(r'S\d{2}E\d{2}', video_name, re.IGNORECASE)
        if not episode_match:
            return None

        episode_code = episode_match.group(0).upper()
        scene_files = list(self.scene_timestamps_dir.glob(f"*{episode_code}*_scenes.json"))

        if not scene_files:
            return None

        try:
            with open(scene_files[0], "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            self.logger.error(f"Failed to load scene timestamps from {scene_files[0]}: {e}")
            return None

    # pylint: disable=too-many-locals
    def __generate_from_scenes(self, video_path: Path, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        scene_timestamps = data.get("scene_timestamps", {})
        scenes = scene_timestamps.get("scenes", [])

        if not scenes:
            console.print("[yellow]No scene timestamps found, using keyframes instead[/yellow]")
            return self.__generate_from_keyframes(video_path)

        fps = scene_timestamps.get("video_info", {}).get("fps", 30)

        frame_requests = []
        for i, scene in enumerate(scenes):
            start_frame = scene.get("start", {}).get("frame", 0)
            end_frame = scene.get("end", {}).get("frame", start_frame + scene.get("frame_count", 1))
            frame_count = scene.get("frame_count", 1)

            if frame_count <= 1:
                frame_requests.append({
                    "frame_number": start_frame,
                    "timestamp": float(start_frame / fps),
                    "type": "scene_single",
                    "scene_number": i,
                })
                continue

            for frame_idx in range(self.frames_per_scene):
                position = frame_idx / (self.frames_per_scene - 1) if self.frames_per_scene > 1 else 0.0
                frame_number = int(start_frame + position * (frame_count - 1))

                frame_type = "scene_start" if frame_idx == 0 else (
                    "scene_end" if frame_idx == self.frames_per_scene - 1 else f"scene_mid_{frame_idx}"
                )

                frame_requests.append({
                    "frame_number": frame_number,
                    "timestamp": float(frame_number / fps),
                    "type": frame_type,
                    "scene_number": i,
                })

        if not frame_requests:
            return []

        console.print(f"[cyan]Extracting {len(frame_requests)} frames ({self.frames_per_scene} per scene from {len(scenes)} scenes)[/cyan]")

        try:
            vr = decord.VideoReader(str(video_path), ctx=decord.cpu(0))
            frame_indices = [req["frame_number"] for req in frame_requests]
            frames_tensor = vr.get_batch(frame_indices)

            embeddings = []
            for batch_start in range(0, len(frame_requests), self.batch_size):
                batch_end = min(batch_start + self.batch_size, len(frame_requests))
                batch_frames = frames_tensor[batch_start:batch_end]
                batch_requests = frame_requests[batch_start:batch_end]

                try:
                    batch_embeddings = self.__encode_frames_batch(batch_frames)

                    for req, emb in zip(batch_requests, batch_embeddings):
                        embeddings.append({
                            "frame_number": int(req["frame_number"]),
                            "timestamp": float(req["timestamp"]),
                            "type": req["type"],
                            "scene_number": req["scene_number"],
                            "embedding": emb.tolist(),
                        })

                except (RuntimeError, ValueError, OSError) as e:
                    self.logger.error(f"Failed batch {batch_start}-{batch_end}: {e}")
                    self.logger.error(f"Traceback: {traceback.format_exc()}")

            console.print(f"[green]Generated {len(embeddings)} video embeddings[/green]")
            return embeddings

        except (RuntimeError, ValueError, OSError) as e:
            self.logger.error(f"Failed to process video {video_path}: {e}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return []

    def __generate_from_keyframes(self, video_path: Path) -> List[Dict[str, Any]]:
        vr = decord.VideoReader(str(video_path), ctx=decord.cpu(0))
        fps = vr.get_avg_fps()
        total_frames = len(vr)

        keyframe_interval_frames = int(fps * 5)

        frame_requests = []
        keyframe_count = 0
        for frame_num in range(0, total_frames, keyframe_interval_frames):
            if keyframe_count % self.keyframe_interval == 0:
                frame_requests.append({
                    "frame_number": int(frame_num),
                    "timestamp": float(frame_num / fps),
                    "type": "keyframe",
                })
            keyframe_count += 1

        if not frame_requests:
            return []

        console.print(f"[cyan]Extracting {len(frame_requests)} keyframes (every {self.keyframe_interval * 5}s)[/cyan]")

        try:
            frame_indices = [req["frame_number"] for req in frame_requests]
            frames_tensor = vr.get_batch(frame_indices)

            embeddings = []
            for batch_start in range(0, len(frame_requests), self.batch_size):
                batch_end = min(batch_start + self.batch_size, len(frame_requests))
                batch_frames = frames_tensor[batch_start:batch_end]
                batch_requests = frame_requests[batch_start:batch_end]

                try:
                    batch_embeddings = self.__encode_frames_batch(batch_frames)

                    for req, emb in zip(batch_requests, batch_embeddings):
                        embeddings.append({
                            "frame_number": req["frame_number"],
                            "timestamp": req["timestamp"],
                            "type": req["type"],
                            "embedding": emb.tolist(),
                        })

                except (RuntimeError, ValueError, OSError) as e:
                    self.logger.error(f"Failed batch {batch_start}-{batch_end}: {e}")

            return embeddings

        except (RuntimeError, ValueError, OSError) as e:
            self.logger.error(f"Failed to process video {video_path}: {e}")
            return []

    def __generate_from_color_diff(self, video_path: Path) -> List[Dict[str, Any]]:
        embeddings = []
        vr = decord.VideoReader(str(video_path), ctx=decord.cpu(0))
        fps = vr.get_avg_fps()

        prev_hist = None
        threshold = 0.3

        for frame_num, frame, hist in iterate_frames_with_histogram(str(video_path)):
            if prev_hist is not None:
                diff = np.sum(np.abs(hist - prev_hist))
                if diff > threshold:
                    try:
                        embedding = self.__encode_frame(frame)
                        embeddings.append(
                            {
                                "frame_number": int(frame_num),
                                "timestamp": float(frame_num / fps),
                                "type": "color_change",
                                "embedding": embedding.tolist(),
                            },
                        )
                    except (RuntimeError, ValueError, OSError) as e:
                        self.logger.error(f"Failed to generate video embedding for frame {frame_num}: {e}")

            prev_hist = hist

        return embeddings

    def __encode_text(self, text: str) -> np.ndarray:
        embeddings = self.model.get_text_embeddings(texts=[text])
        return embeddings[0].cpu().numpy()

    def __encode_frames_batch(self, frames_tensor: torch.Tensor) -> List[np.ndarray]:
        batch_size = frames_tensor.shape[0]
        pil_images = []

        for i in range(batch_size):
            frame_np = frames_tensor[i].cpu().numpy()
            pil_image = Image.fromarray(frame_np)
            pil_images.append(pil_image)

        embeddings_tensor = self.model.get_image_embeddings(images=pil_images)
        return [emb.cpu().numpy() for emb in embeddings_tensor]

    def __encode_frame(self, frame: np.ndarray) -> np.ndarray:
        pil_image = Image.fromarray(frame)
        embeddings = self.model.get_image_embeddings(images=[pil_image])
        return embeddings[0].cpu().numpy()

    def __get_video_path(self, data: Dict[str, Any]) -> Optional[Path]:
        if not self.videos:
            return None

        episode_info = data.get("episode_info", {})
        season = episode_info.get("season")
        episode = episode_info.get("episode_number")

        if season is None or episode is None:
            return None

        if self.videos.is_file():
            return self.videos

        episode_code = f"S{season:02d}E{episode:02d}"

        search_dirs = [
            self.videos / f"Sezon {season}",
            self.videos,
        ]

        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
            for video_file in search_dir.glob("*.mp4"):
                if re.search(episode_code, video_file.name, re.IGNORECASE):
                    return video_file

        return None

    def cleanup(self) -> None:
        console.print("[cyan]Unloading embedding model and clearing GPU memory...[/cyan]")
        if hasattr(self, 'model') and self.model is not None:
            del self.model
            self.model = None
        if hasattr(self, 'processor') and self.processor is not None:
            del self.processor
            self.processor = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        console.print("[green]✓ Embedding model unloaded, GPU memory cleared[/green]")
