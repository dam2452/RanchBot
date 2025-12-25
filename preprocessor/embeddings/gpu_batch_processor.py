from typing import List

from PIL import Image
from rich.progress import Progress
import torch

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

    def process_images_batch(
        self,
        pil_images: List[Image.Image],
        chunk_idx: int,
        progress: Progress,
    ) -> List[List[float]]:
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
                embeddings_tensor = self.model.get_image_embeddings(images=batch_pil, is_query=False)
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
