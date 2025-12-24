from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed,
)
import multiprocessing
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
        console.print(f"[cyan]Initial Batch size: {self.batch_size}[/cyan]")

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

        has_text = bool(data.get("text_embeddings"))
        has_video = bool(data.get("video_embeddings"))

        skip_text = self.generate_text and has_text
        skip_video = self.generate_video and has_video

        if skip_text and skip_video:
            console.print(f"[yellow]Skipping (embeddings already exist): {trans_file.name}[/yellow]")
            return

        if skip_text:
            console.print(f"[yellow]{trans_file.name}: text embeddings exist, skipping text[/yellow]")
        if skip_video:
            console.print(f"[yellow]{trans_file.name}: video embeddings exist, skipping video[/yellow]")

        console.print(f"[cyan]Processing: {trans_file.name}[/cyan]")

        # 1. Generate Text Embeddings
        text_embeddings = data.get("text_embeddings", [])
        if self.generate_text and not skip_text:
            text_embeddings = self.__generate_text_embeddings(data)

        # 2. Generate Video Embeddings
        video_embeddings = data.get("video_embeddings", [])
        if self.generate_video and self.videos and not skip_video:
            video_path = self.__get_video_path(data)

            if video_path and video_path.exists():
                if self.scene_timestamps_dir and "scene_timestamps" not in data:
                    scene_data = self.__load_scene_timestamps(video_path)
                    if scene_data:
                        data["scene_timestamps"] = scene_data

                video_embeddings = self.__generate_video_embeddings(video_path, data)
            else:
                console.print(f"[red]Video not found for: {trans_file.name}[/red]")

        # 3. Save
        data["text_embeddings"] = text_embeddings
        data["video_embeddings"] = video_embeddings

        with open(trans_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        console.print(
            f"[green]{trans_file.name}: {len(text_embeddings)} text, {len(video_embeddings)} video embeddings[/green]",
        )

        self.__cleanup_memory()

    def __generate_text_embeddings(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        segments = data.get("segments", [])
        if not segments:
            return []

        embeddings = []
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

    def __generate_from_scenes(self, video_path: Path, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        scene_timestamps = data.get("scene_timestamps", {})
        scenes = scene_timestamps.get("scenes", [])

        if not scenes:
            console.print("[yellow]No scene timestamps found, falling back to keyframes[/yellow]")
            return self.__generate_from_keyframes(video_path)

        fps = scene_timestamps.get("video_info", {}).get("fps", 30)
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

        return self.__process_video_frames(video_path, frame_requests)

    def __generate_from_keyframes(self, video_path: Path) -> List[Dict[str, Any]]:
        vr = decord.VideoReader(str(video_path), ctx=decord.cpu(0))
        fps = vr.get_avg_fps()
        total_frames = len(vr)
        del vr

        interval_frames = int(fps * 5)
        frame_requests = []

        keyframe_count = 0
        for frame_num in range(0, total_frames, interval_frames):
            if keyframe_count % self.keyframe_interval == 0:
                frame_requests.append(self.__create_request(frame_num, fps, "keyframe"))
            keyframe_count += 1

        return self.__process_video_frames(video_path, frame_requests)

    def __generate_from_color_diff(self, video_path: Path) -> List[Dict[str, Any]]:
        embeddings = []
        vr = decord.VideoReader(str(video_path), ctx=decord.cpu(0))
        fps = vr.get_avg_fps()
        total_frames = len(vr)

        prev_hist = None
        threshold = 0.3
        last_reported = 0

        console.print(f"[cyan]Analyzing {total_frames} frames for color changes...[/cyan]")

        for frame_num, frame, hist in iterate_frames_with_histogram(str(video_path)):
            if prev_hist is not None:
                diff = np.sum(np.abs(hist - prev_hist))
                if diff > threshold:
                    try:
                        embedding = self.__encode_frame_single(frame)
                        embeddings.append(self.__create_result(
                            frame_num, float(frame_num / fps), "color_change", embedding
                        ))
                    except (RuntimeError, ValueError, OSError) as e:
                        self.logger.error(f"Failed video embedding frame {frame_num}: {e}")

            if frame_num - last_reported >= total_frames // 10:
                progress_pct = int(100 * frame_num / total_frames)
                console.print(f"  [cyan]Progress: {frame_num}/{total_frames} ({progress_pct}%)[/cyan]")
                last_reported = frame_num

            prev_hist = hist

        return embeddings

    def __process_video_frames(self, video_path: Path, frame_requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Main engine for processing video frames.
        Handles chunking (RAM safety) and batching (GPU safety).
        """
        if not frame_requests:
            return []

        chunk_size = 512
        total_chunks = (len(frame_requests) + chunk_size - 1) // chunk_size

        console.print(f"[cyan]Processing {len(frame_requests)} frames in {total_chunks} chunks...[/cyan]")

        embeddings = []

        try:
            vr = decord.VideoReader(str(video_path), ctx=decord.cpu(0))

            for chunk_idx in range(total_chunks):
                chunk_start = chunk_idx * chunk_size
                chunk_end = min(chunk_start + chunk_size, len(frame_requests))

                current_requests = frame_requests[chunk_start:chunk_end]
                current_indices = [req["frame_number"] for req in current_requests]

                # 1. Load Images (CPU/RAM Heavy)
                pil_images = self.__load_pil_images(vr, current_indices)

                # 2. Run Inference (GPU Heavy) - with Adaptive Batching
                chunk_embeddings = self.__run_gpu_inference(pil_images, chunk_idx)

                # 3. Merge Results
                for req, emb in zip(current_requests, chunk_embeddings):
                    req_copy = req.copy()
                    req_copy["embedding"] = emb
                    embeddings.append(req_copy)

                # 4. Aggressive Cleanup
                del pil_images
                del chunk_embeddings
                self.__cleanup_memory()

                console.print(f"  [cyan]Chunk {chunk_idx + 1}/{total_chunks} done. Total: {len(embeddings)}[/cyan]")

            del vr
            self.__cleanup_memory()
            return embeddings

        except Exception as e:
            self.logger.error(f"Failed to process video {video_path}: {e}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return []

    def __load_pil_images(self, vr: decord.VideoReader, indices: List[int]) -> List[Image.Image]:
        frames_tensor = vr.get_batch(indices)
        frames_np = frames_tensor.cpu().numpy()
        del frames_tensor

        def convert_to_pil(idx):
            return Image.fromarray(frames_np[idx])

        num_workers = min(8, multiprocessing.cpu_count())
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            pil_images = list(executor.map(convert_to_pil, range(len(frames_np))))

        del frames_np
        gc.collect()
        return pil_images

    def __run_gpu_inference(self, pil_images: List[Image.Image], chunk_idx: int) -> List[List[float]]:
        """
        Runs model inference with ADAPTIVE batch sizing.
        If OOM occurs, it halves the batch size and retries.
        """
        results = []
        current_idx = 0
        total_images = len(pil_images)

        # Start with the configured batch size
        current_batch_size = self.batch_size

        while current_idx < total_images:
            if current_batch_size < 1:
                raise RuntimeError("Batch size reduced to 0. Cannot process image.")

            batch_end = min(current_idx + current_batch_size, total_images)
            batch_pil = pil_images[current_idx:batch_end]

            try:
                with torch.inference_mode():
                    embeddings_tensor = self.model.get_image_embeddings(images=batch_pil)
                    batch_np = embeddings_tensor.cpu().numpy()

                    # Explicitly free graph memory
                    del embeddings_tensor

                    results.extend([emb.tolist() for emb in batch_np])
                    del batch_np

                # Success! Advance pointer
                current_idx = batch_end

            except RuntimeError as e:
                if "out of memory" in str(e).lower():
                    # OOM Detected: Clear cache, reduce batch size, retry SAME index
                    torch.cuda.empty_cache()
                    new_batch_size = current_batch_size // 2
                    console.print(
                        f"[yellow]OOM detected in chunk {chunk_idx}. Reducing batch size: {current_batch_size} -> {new_batch_size}[/yellow]")
                    current_batch_size = new_batch_size
                    continue  # Retry loop with same current_idx but smaller batch
                else:
                    self.logger.error(f"Failed batch in chunk {chunk_idx} at index {current_idx}: {e}")
                    raise e
            except Exception as e:
                self.logger.error(f"Unexpected error in chunk {chunk_idx}: {e}")
                raise e

        return results

    def __create_request(self, frame: int, fps: float, type_name: str, scene_num: int = None) -> Dict[str, Any]:
        req = {
            "frame_number": int(frame),
            "timestamp": float(frame / fps),
            "type": type_name,
        }
        if scene_num is not None:
            req["scene_number"] = scene_num
        return req

    def __create_result(self, frame: int, ts: float, type_name: str, embedding: List[float]) -> Dict[str, Any]:
        return {
            "frame_number": int(frame),
            "timestamp": ts,
            "type": type_name,
            "embedding": embedding
        }

    def __encode_text(self, text: str) -> np.ndarray:
        embeddings = self.model.get_text_embeddings(texts=[text])
        return embeddings[0].cpu().numpy()

    def __encode_frame_single(self, frame: np.ndarray) -> np.ndarray:
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
        search_dirs = [self.videos / f"Sezon {season}", self.videos]

        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
            for video_file in search_dir.glob("*.mp4"):
                if re.search(episode_code, video_file.name, re.IGNORECASE):
                    return video_file
        return None

    def __load_scene_timestamps(self, video_path: Path) -> Optional[Dict[str, Any]]:
        if not self.scene_timestamps_dir or not self.scene_timestamps_dir.exists():
            return None

        episode_match = re.search(r'S\d{2}E\d{2}', video_path.stem, re.IGNORECASE)
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
            self.logger.error(f"Failed to load scene timestamps: {e}")
            return None

    @staticmethod
    def __cleanup_memory() -> None:
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def cleanup(self) -> None:
        console.print("[cyan]Unloading embedding model...[/cyan]")
        self.model = None
        self.processor = None
        self.__cleanup_memory()
        console.print("[green]✓ Model unloaded[/green]")