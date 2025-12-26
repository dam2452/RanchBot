import gc
import json
import logging
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from PIL import Image
import numpy as np
import torch
from transformers import AutoModel

from preprocessor.config.config import settings
from preprocessor.core.base_processor import (
    BaseProcessor,
    OutputSpec,
    ProcessingItem,
)
from preprocessor.core.episode_manager import EpisodeManager
from preprocessor.embeddings.gpu_batch_processor import GPUBatchProcessor
from preprocessor.utils.console import console


class EmbeddingGenerator(BaseProcessor):  # pylint: disable=too-many-instance-attributes
    def __init__(self, args: Dict[str, Any]):
        super().__init__(
            args=args,
            class_name=self.__class__.__name__,
            error_exit_code=9,
            loglevel=logging.DEBUG,
        )

        self.transcription_jsons: Path = self._args["transcription_jsons"]
        self.frames_dir: Path = self._args.get("frames_dir", settings.frame_export.output_dir)
        self.output_dir: Path = self._args.get("output_dir", settings.embedding.default_output_dir)

        self.model_name: str = self._args.get("model", settings.embedding.model_name)
        self.model_revision: str = self._args.get("model_revision", settings.embedding.model_revision)
        self.batch_size: int = self._args.get("batch_size", settings.embedding.batch_size)
        self.resize_height: int = self._args.get("resize_height", settings.embedding.resize_height)
        self.device: str = "cuda"

        self.segments_per_embedding: int = self._args.get("segments_per_embedding", settings.embedding.segments_per_embedding)
        self.generate_text: bool = self._args.get("generate_text", True)
        self.generate_video: bool = self._args.get("generate_video", True)

        episodes_info_json = self._args.get("episodes_info_json")
        self.episode_manager = EpisodeManager(episodes_info_json, self.series_name)

        self.model = None
        self.processor = None
        self.gpu_processor: Optional[GPUBatchProcessor] = None

    def _validate_args(self, args: Dict[str, Any]) -> None:
        if "transcription_jsons" not in args:
            raise ValueError("transcription_jsons is required")
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is not available. This application requires GPU.")

    def cleanup(self) -> None:
        console.print("[cyan]Unloading embedding model...[/cyan]")
        self.model = None
        self.processor = None
        self._cleanup_memory()
        console.print("[green]✓ Model unloaded[/green]")

    def _get_processing_items(self) -> List[ProcessingItem]:
        all_transcription_files = list(self.transcription_jsons.glob("**/*.json"))
        items = []

        for trans_file in all_transcription_files:
            if "_simple.json" in trans_file.name:
                continue
            if not trans_file.name.endswith("_segmented.json"):
                segmented_version = trans_file.parent / f"{trans_file.stem}_segmented.json"
                if segmented_version.exists():
                    continue

            items.append(self._create_transcription_processing_item(trans_file))

        return items

    def _get_expected_outputs(self, item: ProcessingItem) -> List[OutputSpec]:
        outputs = []
        episode_dir = self._get_episode_output_dir(item.input_path)

        if self.generate_text:
            text_output = episode_dir / "embeddings_text.json"
            outputs.append(OutputSpec(path=text_output, required=True))

        if self.generate_video:
            video_output = episode_dir / "embeddings_video.json"
            outputs.append(OutputSpec(path=video_output, required=True))

        return outputs

    def _execute_processing(self, items: List[ProcessingItem]) -> None:
        console.print(f"[cyan]Loading model: {self.model_name}[/cyan]")
        console.print(f"[cyan]Device: {self.device}[/cyan]")
        console.print(f"[cyan]Batch size: {self.batch_size}[/cyan]")

        self._load_model()
        self.gpu_processor = GPUBatchProcessor(self.model, self.batch_size, self.logger, self.device)

        super()._execute_processing(items)
        console.print("[green]Embedding generation completed[/green]")

    def _load_model(self) -> None:
        try:
            self.model = AutoModel.from_pretrained(
                self.model_name,
                torch_dtype="float16",
                device_map="cuda",
                trust_remote_code=True,
            )
            self.model.eval()
            console.print("[green]GME model loaded successfully[/green]")
        except Exception as e:
            self.logger.error(f"Failed to load model: {e}")
            raise

    def _process_item(self, item: ProcessingItem, missing_outputs: List[OutputSpec]) -> None:
        trans_file = item.input_path

        with open(trans_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        has_segments = bool(data.get("segments"))
        segmented_file = trans_file.parent / f"{trans_file.stem}_segmented.json"

        if not has_segments and segmented_file.exists():
            return

        need_text = any("embeddings_text.json" in str(o.path) for o in missing_outputs)
        need_video = any("embeddings_video.json" in str(o.path) for o in missing_outputs)

        text_embeddings = []
        if need_text:
            text_embeddings = self.__generate_text_embeddings(data)

        video_embeddings = []
        if need_video:
            episode_info = data.get("episode_info", {})
            frame_metadata = self.__load_frame_metadata(episode_info)
            if frame_metadata:
                video_embeddings = self.__generate_video_embeddings(episode_info, frame_metadata)

        episode_dir = self._get_episode_output_dir(trans_file)
        text_output = episode_dir / "embeddings_text.json"
        video_output = episode_dir / "embeddings_video.json"
        self.__save_embeddings(data, text_embeddings, video_embeddings, text_output, video_output)
        self._cleanup_memory()

    def __generate_text_embeddings(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        segments = data.get("segments", [])
        if not segments:
            return []

        total_chunks = (len(segments) + self.segments_per_embedding - 1) // self.segments_per_embedding
        embeddings = []

        with self.progress.track_operation(f"Text embeddings ({len(segments)} segments)", total_chunks) as tracker:
            chunk_idx = 0
            for i in range(0, len(segments), self.segments_per_embedding):
                chunk = segments[i: i + self.segments_per_embedding]
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
                    self.logger.error(f"Failed text embedding for segments {i}-{i + len(chunk)}: {e}")

                chunk_idx += 1
                tracker.update(chunk_idx, interval=10)

        return embeddings

    def __encode_text(self, text: str) -> np.ndarray:
        embeddings_tensor = self.model.get_text_embeddings(texts=[text])
        embedding = embeddings_tensor[0].cpu().numpy()
        del embeddings_tensor
        return embedding

    def __load_frame_metadata(self, episode_info_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        season = episode_info_dict.get("season")
        episode = episode_info_dict.get("episode_number")
        if season is None or episode is None:
            return None

        frames_episode_dir = self.frames_dir / f"S{season:02d}" / f"E{episode:02d}"
        metadata_file = frames_episode_dir / "frame_metadata.json"

        if not metadata_file.exists():
            self.logger.warning(f"Frame metadata not found: {metadata_file}")
            return None

        with open(metadata_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def __generate_video_embeddings(self, episode_info_dict: Dict[str, Any], frame_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        frame_requests = frame_metadata.get("frames", [])
        if not frame_requests:
            return []

        season = episode_info_dict.get("season")
        episode = episode_info_dict.get("episode_number")
        frames_episode_dir = self.frames_dir / f"S{season:02d}" / f"E{episode:02d}"

        chunk_size = self.batch_size
        total_chunks = (len(frame_requests) + chunk_size - 1) // chunk_size
        embeddings = []

        with self.progress.track_operation(f"Video embeddings ({len(frame_requests)} frames)", total_chunks) as tracker:
            for chunk_idx in range(total_chunks):
                chunk_start = chunk_idx * chunk_size
                chunk_end = min(chunk_start + chunk_size, len(frame_requests))
                chunk_requests = frame_requests[chunk_start:chunk_end]

                pil_images = self.__load_frames(frames_episode_dir, chunk_requests)
                chunk_embeddings = self.gpu_processor.process_images_batch(pil_images, chunk_idx)

                for request, embedding in zip(chunk_requests, chunk_embeddings):
                    result = request.copy()
                    result["embedding"] = embedding
                    embeddings.append(result)

                del pil_images
                del chunk_embeddings
                self._cleanup_memory()

                tracker.update(chunk_idx + 1, interval=10)

        return embeddings

    @staticmethod
    def __load_frames(frames_dir: Path, frame_requests: List[Dict[str, Any]]) -> List[Image.Image]:
        images = []
        for request in frame_requests:
            frame_num = request["frame_number"]
            frame_path = frames_dir / f"frame_{frame_num:06d}.jpg"
            if frame_path.exists():
                img = Image.open(frame_path)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                images.append(img)
            else:
                images.append(Image.new('RGB', (1, 1)))
        return images

    def _get_episode_output_dir(self, transcription_file: Path) -> Path:
        episode_info_from_file = self.episode_manager.parse_filename(transcription_file)
        if episode_info_from_file:
            season = episode_info_from_file.season
            episode = episode_info_from_file.relative_episode
            return self.output_dir / f"S{season:02d}" / f"E{episode:02d}"
        return self.output_dir / "unknown"

    @staticmethod
    def __save_embeddings(
            data,
        text_embeddings,
        video_embeddings,
        text_output,
        video_output,
    ):
        episode_info = data.get("episode_info", {})
        minimal_episode_info = {
            "season": episode_info.get("season"),
            "episode_number": episode_info.get("episode_number"),
        }

        text_output.parent.mkdir(parents=True, exist_ok=True)

        if text_embeddings:
            text_data = {
                "episode_info": minimal_episode_info,
                "text_embeddings": text_embeddings,
            }
            with open(text_output, "w", encoding="utf-8") as f:
                json.dump(text_data, f, indent=2, ensure_ascii=False)

        if video_embeddings:
            video_data = {
                "episode_info": minimal_episode_info,
                "video_embeddings": video_embeddings,
            }
            with open(video_output, "w", encoding="utf-8") as f:
                json.dump(video_data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def _cleanup_memory() -> None:
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
