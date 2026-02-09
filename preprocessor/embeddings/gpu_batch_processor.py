import time
from typing import (
    Any,
    Dict,
    List,
)

from PIL import Image
import torch

from preprocessor.utils.batch_processor import BatchProcessor
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
        self.batch_processor = BatchProcessor(min(self.batch_size, self.progress_sub_batch_size))

    def __log_vram_usage(self) -> None:
        if torch.cuda.is_available():
            vram_reserved = torch.cuda.memory_reserved(self.device) / 1024**3
            self.max_vram_used = max(self.max_vram_used, vram_reserved)
            self.vram_samples.append(vram_reserved)

    def get_vram_stats(self) -> Dict[str, Any]:
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

    @staticmethod
    def __compute_embeddings(model: Any, batch_pil: List[Image.Image]) -> List[List[float]]:
        inputs = [{"image": img} for img in batch_pil]
        embeddings_tensor = model.process(inputs, normalize=True)
        batch_np = embeddings_tensor.cpu().numpy()
        del embeddings_tensor
        results = [emb.tolist() for emb in batch_np]
        del batch_np
        torch.cuda.empty_cache()
        return results

    @staticmethod
    def __report_batch_progress(
        processed_count: int,
        total_images: int,
        elapsed: float,
        current_batch_size: int,
        batch_start_time: float,
    ) -> None:
        rate = current_batch_size / elapsed if elapsed > 0 else 0
        console.print(
            f"    [dim cyan]→ {processed_count}/{total_images} "
            f"({processed_count / total_images * 100:.0f}%) - {elapsed:.1f}s ({rate:.3f} img/s)[/dim cyan]",
        )

        elapsed_total = time.time() - batch_start_time
        remaining_images = total_images - processed_count
        if processed_count > 0:
            eta = remaining_images / (processed_count / elapsed_total)
            console.print(f"    [dim]Batch ETA: {eta:.0f}s[/dim]")

    def process_images_batch(
        self,
        pil_images: List[Image.Image],
        chunk_idx: int,
    ) -> List[List[float]]:
        total_images = len(pil_images)
        batch_start_time = time.time()
        processed_count = 0

        def _process_sub_batch(batch_pil: List[Image.Image]) -> List[List[float]]:
            nonlocal processed_count
            current_batch_size = len(batch_pil)
            sub_batch_start = time.time()

            try:
                results = self.__compute_embeddings(self.model, batch_pil)
                self.__log_vram_usage()

                processed_count += current_batch_size
                if total_images > self.progress_sub_batch_size:
                    elapsed = time.time() - sub_batch_start
                    self.__report_batch_progress(
                        processed_count,
                        total_images,
                        elapsed,
                        current_batch_size,
                        batch_start_time,
                    )

                return results
            except RuntimeError as e:
                if "out of memory" in str(e).lower():
                    torch.cuda.empty_cache()
                    self.logger.error(
                        f"OOM in chunk {chunk_idx} with batch_size={current_batch_size}. "
                        f"Try reducing progress_sub_batch_size in config.",
                    )
                raise e
            except Exception as e:
                self.logger.error(f"Unexpected error in chunk {chunk_idx}: {e}")
                raise e

        return self.batch_processor.process(pil_images, _process_sub_batch)
