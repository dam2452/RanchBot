import gc
import json
import logging
import threading
import traceback
from pathlib import Path
from queue import Queue
from typing import Any, Dict, List, Optional

import decord
import numpy as np
import torch
from PIL import Image
from rich.progress import Progress
from transformers import AutoModel, AutoProcessor

from preprocessor.config.config import settings
from preprocessor.core.episode_manager import EpisodeManager
from preprocessor.utils.console import console
from preprocessor.utils.error_handling_logger import ErrorHandlingLogger
from preprocessor.utils.video_utils import iterate_frames_with_histogram

decord.bridge.set_bridge('torch')


class EmbeddingGenerator:
    __DEFAULT_DEVICE = "cuda"
    __VIDEO_CHUNK_SIZE = 256
    __RESIZE_BATCH_SIZE = 32
    __COLOR_DIFF_THRESHOLD = 0.3
    __SCENE_FPS_DEFAULT = 30
    __KEYFRAME_INTERVAL_MULTIPLIER = 5

    def __init__(self, args: Dict[str, Any]):
        self.transcription_jsons: Path = args["transcription_jsons"]
        self.videos: Optional[Path] = args.get("videos")
        self.output_dir: Path = args.get("output_dir", settings.embedding.default_output_dir)
        self.scene_timestamps_dir: Optional[Path] = args.get("scene_timestamps_dir")

        self.model_name: str = args.get("model", settings.embedding.model_name)
        self.batch_size: int = args.get("batch_size", settings.embedding.batch_size)
        self.resize_height: int = args.get("resize_height", settings.embedding.resize_height)
        self.prefetch_chunks: int = args.get("prefetch_chunks", settings.embedding.prefetch_chunks)
        self.device: str = self.__DEFAULT_DEVICE

        self.segments_per_embedding: int = args.get("segments_per_embedding", settings.embedding.segments_per_embedding)
        self.keyframe_strategy: str = args.get("keyframe_strategy", settings.embedding.keyframe_strategy)
        self.keyframe_interval: int = args.get("keyframe_interval", settings.embedding.keyframe_interval)
        self.frames_per_scene: int = args.get("frames_per_scene", settings.embedding.frames_per_scene)
        self.generate_text: bool = args.get("generate_text", True)
        self.generate_video: bool = args.get("generate_video", True)

        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is not available. This application requires GPU.")

        self.logger = ErrorHandlingLogger(
            class_name=self.__class__.__name__,
            loglevel=logging.DEBUG,
            error_exit_code=9,
        )

        series_name = args.get("series_name", "unknown")
        episodes_info_json = args.get("episodes_info_json")
        self.episode_manager = EpisodeManager(episodes_info_json, series_name)

        self.model = None
        self.processor = None

    def work(self) -> int:
        try:
            self.__exec()
        except Exception as e:
            self.logger.error(f"Embedding generation failed: {e}")
        return self.logger.finalize()

    def cleanup(self) -> None:
        console.print("[cyan]Unloading embedding model...[/cyan]")
        self.model = None
        self.processor = None
        self.__cleanup_memory()
        console.print("[green]✓ Model unloaded[/green]")

    def __exec(self) -> None:
        console.print(f"[cyan]Loading model: {self.model_name}[/cyan]")
        console.print(f"[cyan]Device: {self.device}[/cyan]")
        console.print(f"[cyan]Batch size: {self.batch_size}[/cyan]")
        console.print(f"[cyan]Frame resize height: {self.resize_height}p[/cyan]")
        console.print(f"[cyan]Prefetch chunks: {self.prefetch_chunks}[/cyan]")

        self.__load_model()

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

        if not transcription_files:
            console.print("[yellow]No transcription files found[/yellow]")
            return

        console.print(f"[blue]Processing {len(transcription_files)} transcriptions...[/blue]")
        self.__process_sequential(transcription_files)
        console.print("[green]Embedding generation completed[/green]")

    def __process_sequential(self, transcription_files: List[Path]) -> None:
        with Progress() as progress:
            task = progress.add_task("[cyan]Processing files", total=len(transcription_files))

            for trans_file in transcription_files:
                try:
                    self.__process_transcription(trans_file, progress)
                except Exception as e:
                    self.logger.error(f"Failed to process {trans_file}: {e}")
                finally:
                    progress.advance(task)

    def __process_transcription(self, trans_file: Path, progress: Progress) -> None:
        with open(trans_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        has_segments = bool(data.get("segments"))
        segmented_file = trans_file.parent / f"{trans_file.stem}_segmented.json"

        if not has_segments and segmented_file.exists():
            progress.console.print(f"[yellow]Skipping {trans_file.name}: no segments, use {segmented_file.name} instead[/yellow]")
            return

        base_name = trans_file.stem.replace("_segmented", "").replace("_simple", "")
        text_output = self.output_dir / f"{base_name}_text.json"
        video_output = self.output_dir / f"{base_name}_video.json"

        skip_text = self.generate_text and text_output.exists()
        skip_video = self.generate_video and video_output.exists()

        if skip_text and skip_video:
            progress.console.print(f"[yellow]Skipping (embeddings already exist): {trans_file.name}[/yellow]")
            return

        if skip_text:
            progress.console.print(f"[yellow]{trans_file.name}: text embeddings exist, skipping text[/yellow]")
        if skip_video:
            progress.console.print(f"[yellow]{trans_file.name}: video embeddings exist, skipping video[/yellow]")

        progress.console.print(f"[cyan]Processing: {trans_file.name}[/cyan]")

        text_embeddings = []
        if self.generate_text and not skip_text:
            text_embeddings = self.__generate_text_embeddings(data, progress)

        video_embeddings = []
        if self.generate_video and self.videos and not skip_video:
            video_path = self.__get_video_path(data)

            if video_path and video_path.exists():
                if self.scene_timestamps_dir and "scene_timestamps" not in data:
                    scene_data = self.__load_scene_timestamps(video_path)
                    if scene_data:
                        data["scene_timestamps"] = scene_data

                video_embeddings = self.__generate_video_embeddings(video_path, data, progress)
            else:
                progress.console.print(f"[red]Video not found for: {trans_file.name}[/red]")

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

        self.__cleanup_memory()

    def __generate_text_embeddings(self, data: Dict[str, Any], progress: Progress) -> List[Dict[str, Any]]:
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
            finally:
                progress.advance(task)

        progress.remove_task(task)
        return embeddings

    def __generate_video_embeddings(self, video_path: Path, data: Dict[str, Any], progress: Progress) -> List[Dict[str, Any]]:
        if self.keyframe_strategy == "scene_changes":
            return self.__generate_from_scenes(video_path, data, progress)
        if self.keyframe_strategy == "keyframes":
            return self.__generate_from_keyframes(video_path, progress)
        if self.keyframe_strategy == "color_diff":
            return self.__generate_from_color_diff(video_path, progress)

        self.logger.error(f"Unknown keyframe strategy: {self.keyframe_strategy}")
        return []

    def __generate_from_scenes(self, video_path: Path, data: Dict[str, Any], progress: Progress) -> List[Dict[str, Any]]:
        scene_timestamps = data.get("scene_timestamps", {})
        scenes = scene_timestamps.get("scenes", [])

        if not scenes:
            progress.console.print("[yellow]No scene timestamps found, falling back to keyframes[/yellow]")
            return self.__generate_from_keyframes(video_path, progress)

        fps = scene_timestamps.get("video_info", {}).get("fps", self.__SCENE_FPS_DEFAULT)
        frame_requests = []

        for i, scene in enumerate(scenes):
            start_frame = scene.get("start", {}).get("frame", 0)
            frame_count = scene.get("frame_count", 1)

            if frame_count <= 1:
                frame_requests.append(self.__create_request(start_frame, fps, "scene_single", i))
                continue

            for frame_idx in range(self.frames_per_scene):
                position = frame_idx / (self.frames_per_scene - 1) if self.frames_per_scene > 1 else 0.0
                frame_number = int(start_frame + position * (frame_count - 1))

                frame_type = "scene_start" if frame_idx == 0 else (
                    "scene_end" if frame_idx == self.frames_per_scene - 1 else f"scene_mid_{frame_idx}"
                )

                frame_requests.append(self.__create_request(frame_number, fps, frame_type, i))

        return self.__process_video_frames(video_path, frame_requests, progress)

    def __generate_from_keyframes(self, video_path: Path, progress: Progress) -> List[Dict[str, Any]]:
        vr = decord.VideoReader(str(video_path), ctx=decord.cpu(0))
        fps = vr.get_avg_fps()
        total_frames = len(vr)
        del vr

        interval_frames = int(fps * self.__KEYFRAME_INTERVAL_MULTIPLIER)
        frame_requests = []

        keyframe_count = 0
        for frame_num in range(0, total_frames, interval_frames):
            if keyframe_count % self.keyframe_interval == 0:
                frame_requests.append(self.__create_request(frame_num, fps, "keyframe"))
            keyframe_count += 1

        return self.__process_video_frames(video_path, frame_requests, progress)

    def __generate_from_color_diff(self, video_path: Path, progress: Progress) -> List[Dict[str, Any]]:
        embeddings = []
        vr = decord.VideoReader(str(video_path), ctx=decord.cpu(0))
        fps = vr.get_avg_fps()
        total_frames = len(vr)

        prev_hist = None
        task = progress.add_task("[blue]Color analysis", total=total_frames)

        for frame_num, frame, hist in iterate_frames_with_histogram(str(video_path)):
            if prev_hist is not None:
                diff = np.sum(np.abs(hist - prev_hist))
                if diff > self.__COLOR_DIFF_THRESHOLD:
                    try:
                        embedding = self.__encode_frame_single(frame)
                        embeddings.append(
                            self.__create_result(
                                frame_num, float(frame_num / fps), "color_change", embedding.tolist(),
                            ),
                        )
                    except (RuntimeError, ValueError, OSError) as e:
                        self.logger.error(f"Failed video embedding frame {frame_num}: {e}")

            progress.update(task, completed=frame_num + 1)
            prev_hist = hist

        progress.remove_task(task)
        return embeddings

    def __process_video_frames(self, video_path: Path, frame_requests: List[Dict[str, Any]], progress: Progress) -> List[Dict[str, Any]]:
        if not frame_requests:
            return []

        chunk_size = self.__VIDEO_CHUNK_SIZE
        total_chunks = (len(frame_requests) + chunk_size - 1) // chunk_size
        task = progress.add_task(f"[magenta]Video chunks ({len(frame_requests)} frames)", total=total_chunks)

        try:
            vr = decord.VideoReader(str(video_path), ctx=decord.cpu(0))

            if self.prefetch_chunks > 0:
                embeddings = self.__process_with_prefetch(vr, frame_requests, chunk_size, total_chunks, progress, task)
            else:
                embeddings = self.__process_sequential_chunks(vr, frame_requests, chunk_size, total_chunks, progress, task)

            del vr
            self.__cleanup_memory()
            progress.remove_task(task)
            return embeddings
        except Exception as e:
            self.logger.error(f"Failed to process video {video_path}: {e}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            progress.remove_task(task)
            return []

    def __process_sequential_chunks(self, vr, frame_requests, chunk_size, total_chunks, progress, task):
        embeddings = []
        for chunk_idx in range(total_chunks):
            chunk_start = chunk_idx * chunk_size
            chunk_end = min(chunk_start + chunk_size, len(frame_requests))
            current_requests = frame_requests[chunk_start:chunk_end]
            current_indices = [req["frame_number"] for req in current_requests]
            pil_images = self.__load_and_preprocess_frames(vr, current_indices)
            self.__process_chunk_embeddings(pil_images, current_requests, chunk_idx, embeddings, progress, task)
        return embeddings

    def __process_with_prefetch(self, vr, frame_requests, chunk_size, total_chunks, progress, task):
        embeddings = []
        prefetch_queue = Queue(maxsize=self.prefetch_chunks)

        def prefetch_worker():
            for prefetch_chunk_idx in range(total_chunks):
                prefetch_chunk_start = prefetch_chunk_idx * chunk_size
                prefetch_chunk_end = min(prefetch_chunk_start + chunk_size, len(frame_requests))
                prefetch_requests = frame_requests[prefetch_chunk_start:prefetch_chunk_end]
                prefetch_indices = [r["frame_number"] for r in prefetch_requests]

                prefetch_images = self.__load_and_preprocess_frames(vr, prefetch_indices)
                prefetch_queue.put((prefetch_chunk_idx, prefetch_requests, prefetch_images))
            prefetch_queue.put(None)

        prefetch_thread = threading.Thread(target=prefetch_worker, daemon=True)
        prefetch_thread.start()

        while True:
            item = prefetch_queue.get()
            if item is None:
                break
            chunk_idx, current_requests, pil_images = item
            self.__process_chunk_embeddings(pil_images, current_requests, chunk_idx, embeddings, progress, task)

        prefetch_thread.join()
        return embeddings

    def __process_chunk_embeddings(self, pil_images, current_requests, chunk_idx, embeddings, progress, task):
        chunk_embeddings = self.__run_gpu_inference(pil_images, chunk_idx, progress)
        for req, emb in zip(current_requests, chunk_embeddings):
            req_copy = req.copy()
            req_copy["embedding"] = emb
            embeddings.append(req_copy)
        del pil_images
        del chunk_embeddings
        self.__cleanup_memory()
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

    def __run_gpu_inference(self, pil_images: List[Image.Image], chunk_idx: int, progress: Progress) -> List[List[float]]:
        results = []
        current_idx = 0
        total_images = len(pil_images)
        current_batch_size = self.batch_size
        batch_task = progress.add_task(f"[yellow]GPU batch (chunk {chunk_idx + 1})", total=total_images)

        while current_idx < total_images:
            if current_batch_size < 1:
                progress.remove_task(batch_task)
                raise RuntimeError("Batch size reduced to 0. Cannot process image.")

            batch_end = min(current_idx + current_batch_size, total_images)
            batch_pil = pil_images[current_idx:batch_end]

            try:
                with torch.inference_mode():
                    embeddings_tensor = self.model.get_image_embeddings(images=batch_pil)
                    batch_np = embeddings_tensor.cpu().numpy()
                    del embeddings_tensor
                    results.extend([emb.tolist() for emb in batch_np])
                    del batch_np
                progress.update(batch_task, completed=batch_end)
                current_idx = batch_end
            except RuntimeError as e:
                if "out of memory" in str(e).lower():
                    torch.cuda.empty_cache()
                    new_batch_size = current_batch_size // 2
                    progress.console.print(
                        f"[yellow]OOM in chunk {chunk_idx}: batch {current_batch_size} -> {new_batch_size}[/yellow]",
                    )
                    current_batch_size = new_batch_size
                    continue
                self.logger.error(f"Failed batch in chunk {chunk_idx} at index {current_idx}: {e}")
                progress.remove_task(batch_task)
                raise e
            except Exception as e:
                self.logger.error(f"Unexpected error in chunk {chunk_idx}: {e}")
                progress.remove_task(batch_task)
                raise e

        progress.remove_task(batch_task)
        return results

    def __encode_text(self, text: str) -> np.ndarray:
        embeddings = self.model.get_text_embeddings(texts=[text])
        return embeddings[0].cpu().numpy()

    def __encode_frame_single(self, frame: np.ndarray) -> np.ndarray:
        pil_image = Image.fromarray(frame)
        embeddings = self.model.get_image_embeddings(images=[pil_image])
        return embeddings[0].cpu().numpy()

    def __load_and_preprocess_frames(self, vr: decord.VideoReader, indices: List[int]) -> List[Image.Image]:
        frames_data = vr.get_batch(indices)
        if isinstance(frames_data, torch.Tensor):
            frames_tensor = frames_data
        else:
            frames_np = frames_data.asnumpy() if hasattr(frames_data, 'asnumpy') else np.array(frames_data)
            frames_tensor = torch.from_numpy(frames_np)

        if self.resize_height > 0:
            frames_tensor = self.__resize_frames_batched(frames_tensor)

        if isinstance(frames_tensor, torch.Tensor):
            if frames_tensor.is_cuda:
                frames_np = frames_tensor.cpu().numpy()
            else:
                frames_np = frames_tensor.numpy()
        else:
            frames_np = frames_tensor

        del frames_tensor
        pil_images = [Image.fromarray(frame) for frame in frames_np]
        del frames_np
        gc.collect()
        return pil_images

    def __resize_frames_batched(self, frames_tensor: torch.Tensor) -> torch.Tensor:
        num_frames = frames_tensor.shape[0]
        resized_frames = []
        for i in range(0, num_frames, self.__RESIZE_BATCH_SIZE):
            batch_end = min(i + self.__RESIZE_BATCH_SIZE, num_frames)
            batch = frames_tensor[i:batch_end]
            resized_batch = self.__resize_frames_gpu(batch)
            resized_frames.append(resized_batch)
            del batch
            torch.cuda.empty_cache()
        result = torch.cat(resized_frames, dim=0)
        resized_frames.clear()
        del resized_frames
        torch.cuda.empty_cache()
        return result

    def __resize_frames_gpu(self, frames_tensor: torch.Tensor) -> torch.Tensor:
        if not isinstance(frames_tensor, torch.Tensor):
            raise TypeError(f"Expected torch.Tensor, got {type(frames_tensor)}")

        device = torch.device(self.device)
        if not frames_tensor.is_cuda:
            frames_tensor = frames_tensor.to(device)

        frames_float = frames_tensor.float() / 255.0
        frames_chw = frames_float.permute(0, 3, 1, 2)
        _, _, orig_h, orig_w = frames_chw.shape
        aspect_ratio = orig_w / orig_h
        new_h = self.resize_height
        new_w = int(new_h * aspect_ratio)

        resized = torch.nn.functional.interpolate(
            frames_chw,
            size=(new_h, new_w),
            mode='bilinear',
            align_corners=False,
        )
        resized_hwc = (resized.permute(0, 2, 3, 1) * 255.0).byte().cpu()
        del frames_float, frames_chw, resized
        torch.cuda.empty_cache()
        return resized_hwc

    def __get_video_path(self, data: Dict[str, Any]) -> Optional[Path]:
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

    def __load_scene_timestamps(self, video_path: Path) -> Optional[Dict[str, Any]]:
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
    def __create_request(frame: int, fps: float, type_name: str, scene_num: int = None) -> Dict[str, Any]:
        req = {
            "frame_number": int(frame),
            "timestamp": float(frame / fps),
            "type": type_name,
        }
        if scene_num is not None:
            req["scene_number"] = scene_num
        return req

    @staticmethod
    def __create_result(frame: int, ts: float, type_name: str, embedding: List[float]) -> Dict[str, Any]:
        return {
            "frame_number": int(frame),
            "timestamp": ts,
            "type": type_name,
            "embedding": embedding,
        }

    @staticmethod
    def __cleanup_memory() -> None:
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
