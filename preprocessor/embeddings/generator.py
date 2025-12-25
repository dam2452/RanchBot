import gc
import json
import logging
from pathlib import Path
from queue import Queue
import threading
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

import decord
import numpy as np
from rich.progress import Progress
import torch
from transformers import (
    AutoModel,
    AutoProcessor,
)

from preprocessor.config.config import settings
from preprocessor.core.base_processor import BaseProcessor
from preprocessor.core.enums import KeyframeStrategy
from preprocessor.core.episode_manager import EpisodeManager
from preprocessor.embeddings.frame_processor import FrameProcessor
from preprocessor.embeddings.gpu_batch_processor import GPUBatchProcessor
from preprocessor.embeddings.strategies.strategy_factory import KeyframeStrategyFactory
from preprocessor.utils.console import console


class EmbeddingGenerator(BaseProcessor):  # pylint: disable=too-many-instance-attributes
    def __init__(self, args: Dict[str, Any]):
        super().__init__(
            args=args,
            class_name=self.__class__.__name__,
            error_exit_code=9,
            loglevel=logging.DEBUG,
        )
        decord.bridge.set_bridge('torch')

        self.transcription_jsons: Path = self._args["transcription_jsons"]
        self.videos: Optional[Path] = self._args.get("videos")
        self.output_dir: Path = self._args.get("output_dir", settings.embedding.default_output_dir)
        self.scene_timestamps_dir: Optional[Path] = self._args.get("scene_timestamps_dir")

        self.model_name: str = self._args.get("model", settings.embedding.model_name)
        self.model_revision: str = self._args.get("model_revision", settings.embedding.model_revision)
        self.batch_size: int = self._args.get("batch_size", settings.embedding.batch_size)
        self.resize_height: int = self._args.get("resize_height", settings.embedding.resize_height)
        self.prefetch_chunks: int = self._args.get("prefetch_chunks", settings.embedding.prefetch_chunks)
        self.device: str = "cuda"

        self.segments_per_embedding: int = self._args.get("segments_per_embedding", settings.embedding.segments_per_embedding)
        keyframe_strategy_str = self._args.get("keyframe_strategy", settings.embedding.keyframe_strategy)
        self.keyframe_strategy = KeyframeStrategy(keyframe_strategy_str)
        self.keyframe_interval: int = self._args.get("keyframe_interval", settings.embedding.keyframe_interval)
        self.frames_per_scene: int = self._args.get("frames_per_scene", settings.embedding.frames_per_scene)
        self.generate_text: bool = self._args.get("generate_text", True)
        self.generate_video: bool = self._args.get("generate_video", True)

        episodes_info_json = self._args.get("episodes_info_json")
        self.episode_manager = EpisodeManager(episodes_info_json, self.series_name)

        self.model = None
        self.processor = None
        self.frame_processor: Optional[FrameProcessor] = None
        self.gpu_processor: Optional[GPUBatchProcessor] = None
        self.strategy = None

    def _validate_args(self, args: Dict[str, Any]) -> None:
        if "transcription_jsons" not in args:
            raise ValueError("transcription_jsons is required")
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is not available. This application requires GPU.")

    def _execute(self) -> None:
        console.print(f"[cyan]Loading model: {self.model_name}[/cyan]")
        console.print(f"[cyan]Device: {self.device}[/cyan]")
        console.print(f"[cyan]Batch size: {self.batch_size}[/cyan]")
        console.print(f"[cyan]Frame resize height: {self.resize_height}p[/cyan]")
        console.print(f"[cyan]Prefetch chunks: {self.prefetch_chunks}[/cyan]")

        self._load_model()
        self.frame_processor = FrameProcessor(self.resize_height, self.device)
        self.gpu_processor = GPUBatchProcessor(self.model, self.batch_size, self.logger)
        self.strategy = KeyframeStrategyFactory.create(
            self.keyframe_strategy,
            self.keyframe_interval,
            self.frames_per_scene,
        )

        transcription_files = self._get_transcription_files()
        if not transcription_files:
            console.print("[yellow]No transcription files found[/yellow]")
            return

        console.print(f"[blue]Processing {len(transcription_files)} transcriptions...[/blue]")
        self._process_sequential(transcription_files)
        console.print("[green]Embedding generation completed[/green]")

    def cleanup(self) -> None:
        console.print("[cyan]Unloading embedding model...[/cyan]")
        self.model = None
        self.processor = None
        self._cleanup_memory()
        console.print("[green]✓ Model unloaded[/green]")

    def _get_transcription_files(self) -> List[Path]:
        all_transcription_files = list(self.transcription_jsons.glob("**/*.json"))
        transcription_files = []
        for f in all_transcription_files:
            if "_simple.json" in f.name:
                continue
            if not f.name.endswith("_segmented.json"):
                segmented_version = f.parent / f"{f.stem}_segmented.json"
                if segmented_version.exists():
                    continue
            transcription_files.append(f)
        return transcription_files

    def _process_sequential(self, transcription_files: List[Path]) -> None:
        with Progress() as progress:
            task = progress.add_task("[cyan]Processing files", total=len(transcription_files))

            for trans_file in transcription_files:
                try:
                    self._process_transcription(trans_file, progress)
                except Exception as e:  # pylint: disable=broad-exception-caught
                    self.logger.error(f"Failed to process {trans_file}: {e}")
                finally:
                    progress.advance(task)

    def _process_transcription(self, trans_file: Path, progress: Progress) -> None:
        with open(trans_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        has_segments = bool(data.get("segments"))
        segmented_file = trans_file.parent / f"{trans_file.stem}_segmented.json"

        if not has_segments and segmented_file.exists():
            progress.console.print(f"[yellow]Skipping {trans_file.name}: no segments[/yellow]")
            return

        base_name = trans_file.stem.replace("_segmented", "").replace("_simple", "")
        text_output = self.output_dir / f"{base_name}_text.json"
        video_output = self.output_dir / f"{base_name}_video.json"

        skip_text = self.generate_text and text_output.exists()
        skip_video = self.generate_video and video_output.exists()

        if skip_text and skip_video:
            progress.console.print(f"[yellow]Skipping (embeddings exist): {trans_file.name}[/yellow]")
            return

        progress.console.print(f"[cyan]Processing: {trans_file.name}[/cyan]")

        text_embeddings = []
        if self.generate_text and not skip_text:
            text_embeddings = self._generate_text_embeddings(data, progress)

        video_embeddings = []
        if self.generate_video and self.videos and not skip_video:
            video_path = self._get_video_path(data)

            if video_path and video_path.exists():
                if self.scene_timestamps_dir and "scene_timestamps" not in data:
                    scene_data = self._load_scene_timestamps(video_path)
                    if scene_data:
                        data["scene_timestamps"] = scene_data

                video_embeddings = self._generate_video_embeddings(video_path, data, progress)
            else:
                progress.console.print(f"[red]Video not found: {trans_file.name}[/red]")

        self._save_embeddings(data, text_embeddings, video_embeddings, text_output, video_output, progress)
        self._cleanup_memory()

    def _generate_text_embeddings(self, data: Dict[str, Any], progress: Progress) -> List[Dict[str, Any]]:
        segments = data.get("segments", [])
        if not segments:
            return []

        embeddings = []
        num_chunks = (len(segments) + self.segments_per_embedding - 1) // self.segments_per_embedding
        task = progress.add_task("[green]Text embeddings", total=num_chunks)

        for i in range(0, len(segments), self.segments_per_embedding):
            chunk = segments[i: i + self.segments_per_embedding]
            combined_text = " ".join([seg.get("text", "") for seg in chunk])

            if not combined_text.strip():
                progress.advance(task)
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
            except (RuntimeError, ValueError, OSError) as e:
                self.logger.error(f"Failed text embedding for segments {i}-{i + len(chunk)}: {e}")
            finally:
                progress.advance(task)

        progress.remove_task(task)
        return embeddings

    def _generate_video_embeddings(self, video_path: Path, data: Dict[str, Any], progress: Progress) -> List[Dict[str, Any]]:
        frame_requests = self.strategy.extract_frame_requests(video_path, data, progress)
        return self._process_video_frames(video_path, frame_requests, progress)

    def _process_video_frames(self, video_path: Path, frame_requests: List[Dict[str, Any]], progress: Progress) -> List[Dict[str, Any]]:
        if not frame_requests:
            return []

        chunk_size = settings.embedding.video_chunk_size
        total_chunks = (len(frame_requests) + chunk_size - 1) // chunk_size
        task = progress.add_task(f"[magenta]Video chunks ({len(frame_requests)} frames)", total=total_chunks)

        try:
            vr = decord.VideoReader(str(video_path), ctx=decord.cpu(0))

            if self.prefetch_chunks > 0:
                embeddings = self._process_with_prefetch(vr, frame_requests, chunk_size, total_chunks, progress, task)
            else:
                embeddings = self._process_sequential_chunks(vr, frame_requests, chunk_size, total_chunks, progress, task)

            del vr
            self._cleanup_memory()
            progress.remove_task(task)
            return embeddings
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error(f"Failed to process video {video_path}: {e}")
            progress.remove_task(task)
            return []

    def _process_sequential_chunks(self, vr, frame_requests, chunk_size, total_chunks, progress, task):
        embeddings = []
        for chunk_idx in range(total_chunks):
            chunk_start = chunk_idx * chunk_size
            chunk_end = min(chunk_start + chunk_size, len(frame_requests))
            current_requests = frame_requests[chunk_start:chunk_end]
            current_indices = [req["frame_number"] for req in current_requests]
            pil_images = self.frame_processor.load_and_preprocess_frames(vr, current_indices)
            self._process_chunk_embeddings(pil_images, current_requests, chunk_idx, embeddings, progress, task)
        return embeddings

    def _process_with_prefetch(self, vr, frame_requests, chunk_size, total_chunks, progress, task):
        embeddings = []
        prefetch_queue = Queue(maxsize=self.prefetch_chunks)

        def prefetch_worker():
            for prefetch_chunk_idx in range(total_chunks):
                prefetch_chunk_start = prefetch_chunk_idx * chunk_size
                prefetch_chunk_end = min(prefetch_chunk_start + chunk_size, len(frame_requests))
                prefetch_requests = frame_requests[prefetch_chunk_start:prefetch_chunk_end]
                prefetch_indices = [r["frame_number"] for r in prefetch_requests]

                prefetch_images = self.frame_processor.load_and_preprocess_frames(vr, prefetch_indices)
                prefetch_queue.put((prefetch_chunk_idx, prefetch_requests, prefetch_images))
            prefetch_queue.put(None)

        prefetch_thread = threading.Thread(target=prefetch_worker, daemon=True)
        prefetch_thread.start()

        while True:
            item = prefetch_queue.get()
            if item is None:
                break
            chunk_idx, current_requests, pil_images = item
            self._process_chunk_embeddings(pil_images, current_requests, chunk_idx, embeddings, progress, task)

        prefetch_thread.join()
        return embeddings

    def _process_chunk_embeddings(self, pil_images, current_requests, chunk_idx, embeddings, progress, task):
        chunk_embeddings = self.gpu_processor.process_images_batch(pil_images, chunk_idx, progress)
        for req, emb in zip(current_requests, chunk_embeddings):
            req_copy = req.copy()
            req_copy["embedding"] = emb
            embeddings.append(req_copy)
        del pil_images
        del chunk_embeddings
        self._cleanup_memory()
        progress.advance(task)

    def _save_embeddings(self, data, text_embeddings, video_embeddings, text_output, video_output, progress):
        episode_info = data.get("episode_info", {})
        minimal_episode_info = {
            "season": episode_info.get("season"),
            "episode_number": episode_info.get("episode_number"),
        }

        self.output_dir.mkdir(parents=True, exist_ok=True)

        if text_embeddings:
            text_data = {
                "episode_info": minimal_episode_info,
                "text_embeddings": text_embeddings,
            }
            with open(text_output, "w", encoding="utf-8") as f:
                json.dump(text_data, f, indent=2, ensure_ascii=False)
            progress.console.print(f"[green]Saved {len(text_embeddings)} text embeddings → {text_output.name}[/green]")

        if video_embeddings:
            video_data = {
                "episode_info": minimal_episode_info,
                "video_embeddings": video_embeddings,
            }
            with open(video_output, "w", encoding="utf-8") as f:
                json.dump(video_data, f, indent=2, ensure_ascii=False)
            progress.console.print(f"[green]Saved {len(video_embeddings)} video embeddings → {video_output.name}[/green]")

    def _load_model(self) -> None:
        try:
            self.processor = AutoProcessor.from_pretrained(
                self.model_name,
                revision=self.model_revision,
                trust_remote_code=True,
                use_fast=True
            )
            self.model = AutoModel.from_pretrained(
                self.model_name,
                revision=self.model_revision,
                torch_dtype="float16",
                device_map="cuda",
                trust_remote_code=True,
            )
            self.model.eval()
            console.print(f"[green]Model loaded successfully (revision: {self.model_revision})[/green]")
        except Exception as e:
            self.logger.error(f"Failed to load model: {e}")
            raise

    def _encode_text(self, text: str) -> np.ndarray:
        embeddings = self.model.get_text_embeddings(texts=[text])
        return embeddings[0].cpu().numpy()

    def _get_video_path(self, data: Dict[str, Any]) -> Optional[Path]:
        if not self.videos:
            return None
        episode_info_dict = data.get("episode_info", {})
        season = episode_info_dict.get("season")
        episode = episode_info_dict.get("episode_number")
        if season is None or episode is None:
            return None
        episode_info = self.episode_manager.get_episode_by_season_and_relative(season, episode)
        if not episode_info:
            return None
        return EpisodeManager.find_video_file(episode_info, self.videos)

    def _load_scene_timestamps(self, video_path: Path) -> Optional[Dict[str, Any]]:
        if not self.scene_timestamps_dir or not self.scene_timestamps_dir.exists():
            return None
        episode_info = self.episode_manager.parse_filename(video_path)
        if not episode_info:
            return None
        scene_file = EpisodeManager.find_scene_timestamps_file(episode_info, self.scene_timestamps_dir)
        if not scene_file:
            return None
        try:
            with open(scene_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            self.logger.error(f"Failed to load scene timestamps: {e}")
            return None

    @staticmethod
    def _cleanup_memory() -> None:
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
