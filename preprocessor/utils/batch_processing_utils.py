from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import (
    Any,
    Dict,
    Iterator,
    List,
    Tuple,
)

from PIL import Image

from preprocessor.embeddings.gpu_batch_processor import GPUBatchProcessor
from preprocessor.embeddings.image_hasher import PerceptualHasher
from preprocessor.utils.console import console
from preprocessor.utils.frame_utils import load_frames_from_requests


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

        if (chunk_idx + 1) % 10 == 0:
            console.print(f"  Hashed {chunk_idx + 1}/{total_chunks} batches")

    console.print(f"[green]✓ Computed {len(results)} hashes[/green]")
    return results


def compute_embeddings_in_batches(
    frames_dir: Path,
    frame_requests: List[Dict[str, Any]],
    gpu_processor: GPUBatchProcessor,
    batch_size: int,
    image_hashes: Dict[int, str],
) -> List[Dict[str, Any]]:
    total_chunks = (len(frame_requests) + batch_size - 1) // batch_size
    embeddings = []

    console.print(f"[cyan]Computing embeddings for {len(frame_requests)} frames in {total_chunks} batches (with prefetch)[/cyan]")

    for chunk_idx, chunk_requests, pil_images in _prefetch_batches(
        frames_dir, frame_requests, batch_size, convert_rgb=True, prefetch_count=2,
    ):
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

        if (chunk_idx + 1) % 10 == 0:
            console.print(f"  Embedded {chunk_idx + 1}/{total_chunks} batches")

    console.print(f"[green]✓ Computed {len(embeddings)} embeddings[/green]")
    return embeddings
