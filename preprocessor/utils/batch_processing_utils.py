from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
)

from preprocessor.embeddings.gpu_batch_processor import GPUBatchProcessor
from preprocessor.embeddings.image_hasher import PerceptualHasher
from preprocessor.utils.console import console
from preprocessor.utils.frame_utils import load_frames_from_requests


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
    cleanup_fn,
) -> List[Dict[str, Any]]:
    total_chunks = (len(frame_requests) + batch_size - 1) // batch_size
    embeddings = []

    console.print(f"[cyan]Computing embeddings for {len(frame_requests)} frames in {total_chunks} batches[/cyan]")

    for chunk_idx in range(total_chunks):
        chunk_start = chunk_idx * batch_size
        chunk_end = min(chunk_start + batch_size, len(frame_requests))
        chunk_requests = frame_requests[chunk_start:chunk_end]

        pil_images = load_frames_from_requests(frames_dir, chunk_requests, convert_rgb=True)
        chunk_embeddings = gpu_processor.process_images_batch(pil_images, chunk_idx)

        for request, embedding in zip(chunk_requests, chunk_embeddings):
            result = request.copy()
            result["embedding"] = embedding

            frame_num = request.get("frame_number")
            if frame_num is not None and frame_num in image_hashes:
                result["perceptual_hash"] = image_hashes[frame_num]

            embeddings.append(result)

        del pil_images
        del chunk_embeddings
        cleanup_fn()

        if (chunk_idx + 1) % 10 == 0:
            console.print(f"  Embedded {chunk_idx + 1}/{total_chunks} batches")

    console.print(f"[green]✓ Computed {len(embeddings)} embeddings[/green]")
    return embeddings
