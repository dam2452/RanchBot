import time
from typing import List

from PIL import Image
import torch

from preprocessor.utils.console import console
from preprocessor.utils.error_handling_logger import ErrorHandlingLogger


class GPUBatchProcessor:
    def __init__(
        self,
        model,
        batch_size: int,
        logger: ErrorHandlingLogger,
        device: str,
        progress_sub_batch_size: int = 100,
    ):
        self.model = model
        self.batch_size = batch_size
        self.progress_sub_batch_size = progress_sub_batch_size
        self.logger = logger
        self.device = device
        self.max_vram_used = 0.0
        self.vram_samples = []

    def _log_vram_usage(self) -> None:
        if torch.cuda.is_available():
            vram_reserved = torch.cuda.memory_reserved(self.device) / 1024**3
            self.max_vram_used = max(self.max_vram_used, vram_reserved)
            self.vram_samples.append(vram_reserved)

    def get_vram_stats(self) -> dict:
        if not self.vram_samples:
            return {}
        return {
            "max_vram_gb": round(self.max_vram_used, 2),
            "avg_vram_gb": round(sum(self.vram_samples) / len(self.vram_samples), 2),
            "samples": len(self.vram_samples),
        }

    def suggest_optimal_batch_size(self, target_vram_gb: float = 21.0) -> int:
        if not self.vram_samples:
            return self.batch_size

        avg_vram = sum(self.vram_samples) / len(self.vram_samples)
        if avg_vram <= 0:
            return self.batch_size

        vram_ratio = target_vram_gb / avg_vram
        suggested = int(self.batch_size * vram_ratio * 0.9)

        suggested = max(50, min(suggested, 1000))

        return suggested

    def process_images_batch(  # pylint: disable=too-many-locals
        self,
        pil_images: List[Image.Image],
        chunk_idx: int,
    ) -> List[List[float]]:
        results = []
        total_images = len(pil_images)
        effective_batch_size = min(self.batch_size, self.progress_sub_batch_size)
        batch_start_time = time.time()

        for sub_idx in range(0, total_images, effective_batch_size):
            sub_end = min(sub_idx + effective_batch_size, total_images)
            batch_pil = pil_images[sub_idx:sub_end]
            current_batch_size = len(batch_pil)

            try:  # pylint: disable=too-many-try-statements
                sub_batch_start = time.time()

                inputs = [{"image": img} for img in batch_pil]
                embeddings_tensor = self.model.process(inputs, normalize=True)
                self._log_vram_usage()
                batch_np = embeddings_tensor.cpu().numpy()
                del embeddings_tensor
                results.extend([emb.tolist() for emb in batch_np])
                del batch_np
                torch.cuda.empty_cache()

                if total_images > self.progress_sub_batch_size:
                    elapsed = time.time() - sub_batch_start
                    rate = current_batch_size / elapsed if elapsed > 0 else 0
                    console.print(
                        f"    [dim cyan]→ {sub_idx + 1}-{sub_end}/{total_images} "
                        f"({sub_end / total_images * 100:.0f}%) - {elapsed:.1f}s ({rate:.1f} img/s)[/dim cyan]",
                    )

                    elapsed_total = time.time() - batch_start_time
                    if sub_end < total_images:
                        remaining_images = total_images - sub_end
                        eta = remaining_images / (sub_end / elapsed_total) if elapsed_total > 0 else 0
                        console.print(f"    [dim]Batch ETA: {eta:.0f}s[/dim]")
            except RuntimeError as e:
                if "out of memory" in str(e).lower():
                    torch.cuda.empty_cache()
                    self.logger.error(
                        f"OOM in chunk {chunk_idx} with batch_size={current_batch_size}. "
                        f"Try reducing progress_sub_batch_size in config.",
                    )
                raise e
            except Exception as e:
                self.logger.error(f"Unexpected error in chunk {chunk_idx} sub-batch {sub_idx}-{sub_end}: {e}")
                raise e

        return results
