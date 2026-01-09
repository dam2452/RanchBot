from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import time
from typing import (
    Any,
    Dict,
    Iterator,
    List,
    Optional,
    Tuple,
)

from PIL import Image

from preprocessor.embeddings.gpu_batch_processor import GPUBatchProcessor
from preprocessor.embeddings.image_hasher import PerceptualHasher
from preprocessor.utils.console import console
from preprocessor.utils.frame_utils import load_frames_from_requests
from preprocessor.utils.time_utils import format_time_hms


def _prefetch_batches(
    frames_dir: Path,
    frame_requests: List[Dict[str, Any]],
    batch_size: int,
    convert_rgb: bool = False,
    prefetch_count: int = 2,
) -> Iterator[Tuple[int, List[Dict[str, Any]], List[Image.Image]]]:
    total_chunks = (len(frame_requests) + batch_size - 1) // batch_size

    with ThreadPoolExecutor(max_workers=prefetch_count) as executor:
        futures = {}

        for chunk_idx in range(total_chunks):
            chunk_start = chunk_idx * batch_size
            chunk_end = min(chunk_start + batch_size, len(frame_requests))
            chunk_requests = frame_requests[chunk_start:chunk_end]

            future = executor.submit(load_frames_from_requests, frames_dir, chunk_requests, convert_rgb)
            futures[chunk_idx] = (chunk_requests, future)

            if len(futures) >= prefetch_count or chunk_idx == total_chunks - 1:
                next_idx = chunk_idx - len(futures) + 1
                chunk_reqs, future = futures.pop(next_idx)
                pil_images = future.result()
                yield next_idx, chunk_reqs, pil_images


def compute_hashes_in_batches(
    frames_dir: Path,
    frame_requests: List[Dict[str, Any]],
    hasher: PerceptualHasher,
    batch_size: int,
) -> List[Dict[str, Any]]:
    total_chunks = (len(frame_requests) + batch_size - 1) // batch_size
    results = []

    console.print(f"[cyan]Computing hashes for {len(frame_requests)} frames in {total_chunks} batches[/cyan]")

    start_time = time.time()

    for chunk_idx in range(total_chunks):
        chunk_start = chunk_idx * batch_size
        chunk_end = min(chunk_start + batch_size, len(frame_requests))
        chunk_requests = frame_requests[chunk_start:chunk_end]

        pil_images = load_frames_from_requests(frames_dir, chunk_requests)
        phashes = hasher.compute_phash_batch(pil_images)

        for request, phash in zip(chunk_requests, phashes):
            result = request.copy()
            result["perceptual_hash"] = phash
            results.append(result)

        del pil_images

        _report_batch_progress(
            chunk_idx + 1,
            total_chunks,
            chunk_idx + 1,
            total_chunks,
            start_time,
        )

    console.print(f"[green]✓ Computed {len(results)} hashes[/green]")
    return results


def compute_embeddings_in_batches(  # pylint: disable=too-many-locals
    frames_dir: Path,
    frame_requests: List[Dict[str, Any]],
    gpu_processor: GPUBatchProcessor,
    batch_size: int,
    image_hashes: Dict[int, str],
    checkpoint_file: Optional[Path] = None,
    checkpoint_interval: int = 20,
    prefetch_count: int = 2,
) -> List[Dict[str, Any]]:
    total_chunks = (len(frame_requests) + batch_size - 1) // batch_size
    embeddings = []
    start_chunk_idx = 0

    if checkpoint_file and checkpoint_file.exists():
        console.print("[yellow]Found checkpoint file, resuming from last saved batch[/yellow]")
        try:
            with open(checkpoint_file, "r", encoding="utf-8") as f:
                checkpoint_data = json.load(f)
            embeddings = checkpoint_data.get("embeddings", [])
            start_chunk_idx = checkpoint_data.get("last_batch_idx", 0) + 1
            console.print(f"[cyan]Resuming from batch {start_chunk_idx}/{total_chunks}[/cyan]")
        except (json.JSONDecodeError, KeyError) as e:
            console.print(f"[yellow]Failed to load checkpoint: {e}. Starting from beginning.[/yellow]")
            start_chunk_idx = 0
            embeddings = []

    console.print(f"[cyan]Computing embeddings for {len(frame_requests)} frames in {total_chunks} batches (with prefetch={prefetch_count})[/cyan]")

    actual_checkpoint_interval = min(checkpoint_interval, max(1, total_chunks // 2))
    if actual_checkpoint_interval != checkpoint_interval:
        console.print(f"[dim cyan]Adjusted checkpoint interval: {actual_checkpoint_interval} (every ~50% of batches)[/dim cyan]")

    start_time = time.time()
    processed_batches = 0
    batches_to_process = total_chunks - start_chunk_idx

    for chunk_idx, chunk_requests, pil_images in _prefetch_batches(
        frames_dir, frame_requests, batch_size, convert_rgb=True, prefetch_count=prefetch_count,
    ):
        if chunk_idx < start_chunk_idx:
            continue

        chunk_embeddings = gpu_processor.process_images_batch(pil_images, chunk_idx)

        for request, embedding in zip(chunk_requests, chunk_embeddings):
            result = {
                **request,
                "embedding": embedding,
            }

            frame_num = request.get("frame_number")
            if frame_num is not None and frame_num in image_hashes:
                result["perceptual_hash"] = image_hashes[frame_num]

            embeddings.append(result)

        del pil_images
        del chunk_embeddings

        processed_batches += 1
        _report_batch_progress(
            processed_batches,
            batches_to_process,
            chunk_idx + 1,
            total_chunks,
            start_time,
        )

        if checkpoint_file and (chunk_idx + 1) % actual_checkpoint_interval == 0:
            _save_checkpoint(checkpoint_file, chunk_idx, embeddings)

    if checkpoint_file and checkpoint_file.exists():
        checkpoint_file.unlink()
        console.print("[cyan]Checkpoint file removed[/cyan]")

    vram_stats = gpu_processor.get_vram_stats()
    if vram_stats:
        console.print(
            f"[cyan]VRAM usage: max={vram_stats['max_vram_gb']}GB, "
            f"avg={vram_stats['avg_vram_gb']}GB[/cyan]",
        )
        suggested_batch = gpu_processor.suggest_optimal_batch_size(target_vram_gb=21.0)
        if suggested_batch != batch_size:
            console.print(
                f"[yellow]Suggested batch_size for 21GB VRAM target: {suggested_batch} "
                f"(current: {batch_size})[/yellow]",
            )

    console.print(f"[green]✓ Computed {len(embeddings)} embeddings[/green]")
    return embeddings


def _report_batch_progress(
    processed: int,
    total_to_process: int,
    current_batch: int,
    total_batches: int,
    start_time: float,
) -> None:
    elapsed = time.time() - start_time
    percent = (processed / total_to_process * 100) if total_to_process > 0 else 0

    if 0 < processed < total_to_process:
        rate = processed / elapsed if elapsed > 0 else 0
        remaining = total_to_process - processed
        eta_seconds = remaining / rate if rate > 0 else 0
        eta = format_time_hms(eta_seconds) if eta_seconds > 0 else "0:00:00"
        rate_str = f"{rate:.2f} batch/s"
    elif processed >= total_to_process:
        eta = "0:00:00"
        rate_str = f"{processed / elapsed:.2f} batch/s" if elapsed > 0 else "N/A"
    else:
        eta = "-:--:--"
        rate_str = "N/A"

    console.print(
        f"  [dim cyan]Batch {current_batch}/{total_batches} "
        f"({percent:.1f}%) | {rate_str} | ETA: {eta}[/dim cyan]",
    )


def _save_checkpoint(checkpoint_file: Path, last_batch_idx: int, embeddings: List[Dict[str, Any]]) -> None:
    checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_data = {
        "last_batch_idx": last_batch_idx,
        "embeddings": embeddings,
    }
    with open(checkpoint_file, "w", encoding="utf-8") as f:
        json.dump(checkpoint_data, f)
    console.print(f"[dim cyan]Checkpoint saved at batch {last_batch_idx + 1}[/dim cyan]")
