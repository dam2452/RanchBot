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
    ):
        self.model = model
        self.batch_size = batch_size
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

    def process_images_batch(
        self,
        pil_images: List[Image.Image],
        chunk_idx: int,
    ) -> List[List[float]]:
        results = []
        current_idx = 0
        total_images = len(pil_images)
        current_batch_size = self.batch_size

        while current_idx < total_images:
            if current_batch_size < 1:
                raise RuntimeError("Batch size reduced to 0. Cannot process image.")

            batch_end = min(current_idx + current_batch_size, total_images)
            batch_pil = pil_images[current_idx:batch_end]

            try:
                inputs = [{"image": img} for img in batch_pil]
                embeddings_tensor = self.model.process(inputs, normalize=True)
                self._log_vram_usage()
                batch_np = embeddings_tensor.cpu().numpy()
                del embeddings_tensor
                results.extend([emb.tolist() for emb in batch_np])
                del batch_np
                current_idx = batch_end
                torch.cuda.empty_cache()
            except RuntimeError as e:
                if "out of memory" in str(e).lower():
                    torch.cuda.empty_cache()
                    new_batch_size = current_batch_size // 2
                    console.print(
                        f"[yellow]OOM in chunk {chunk_idx}: batch {current_batch_size} -> {new_batch_size}[/yellow]",
                    )
                    current_batch_size = new_batch_size
                    continue
                self.logger.error(f"Failed batch in chunk {chunk_idx} at index {current_idx}: {e}")
                raise e
            except Exception as e:
                self.logger.error(f"Unexpected error in chunk {chunk_idx}: {e}")
                raise e

        return results
