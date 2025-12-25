from typing import List

from PIL import Image
import decord
import numpy as np
import torch

from preprocessor.config.config import settings


class FrameProcessor:
    def __init__(self, resize_height: int, device: str):
        self.resize_height = resize_height
        self.device = device

    def load_and_preprocess_frames(
        self,
        vr: decord.VideoReader,
        indices: List[int],
    ) -> List[Image.Image]:
        frames_data = vr.get_batch(indices)
        if isinstance(frames_data, torch.Tensor):
            frames_tensor = frames_data
        else:
            frames_np = frames_data.asnumpy() if hasattr(frames_data, 'asnumpy') else np.array(frames_data)
            frames_tensor = torch.from_numpy(frames_np)

        if self.resize_height > 0:
            frames_tensor = self._resize_frames_batched(frames_tensor)

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
        return pil_images

    def _resize_frames_batched(self, frames_tensor: torch.Tensor) -> torch.Tensor:
        num_frames = frames_tensor.shape[0]
        resized_frames = []
        for i in range(0, num_frames, settings.embedding.resize_batch_size):
            batch_end = min(i + settings.embedding.resize_batch_size, num_frames)
            batch = frames_tensor[i:batch_end]
            resized_batch = self._resize_frames_gpu(batch)
            resized_frames.append(resized_batch)
            del batch
            torch.cuda.empty_cache()
        result = torch.cat(resized_frames, dim=0)
        resized_frames.clear()
        del resized_frames
        torch.cuda.empty_cache()
        return result

    def _resize_frames_gpu(self, frames_tensor: torch.Tensor) -> torch.Tensor:
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
