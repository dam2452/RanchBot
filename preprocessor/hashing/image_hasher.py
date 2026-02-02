import logging
from typing import List

from PIL import Image
import numpy as np
import torch
import torch.nn.functional as F


class PerceptualHasher:
    def __init__(self, device: str = "cuda", hash_size: int = 8):
        self.device = device
        self.hash_size = hash_size
        self.resize_size = hash_size * 4
        self.logger = logging.getLogger(__name__)

    def compute_phash_batch(self, pil_images: List[Image.Image]) -> List[str]:
        if not pil_images:
            return []

        try:
            images_tensor = self.__pil_to_tensor_batch(pil_images)
            hashes = self.__compute_phash_tensor(images_tensor)
            return hashes
        except Exception as e:
            self.logger.error(f"Failed to compute pHash: {e}")
            return ["0" * 16] * len(pil_images)

    def __pil_to_tensor_batch(self, pil_images: List[Image.Image]) -> torch.Tensor:
        tensors = []
        for img in pil_images:
            if img.mode != 'L':
                img = img.convert('L')
            img_resized = img.resize((self.resize_size, self.resize_size), Image.Resampling.LANCZOS)
            img_array = np.array(img_resized, dtype=np.float32)
            tensor = torch.from_numpy(img_array)
            tensors.append(tensor)

        batch_tensor = torch.stack(tensors).unsqueeze(1).to(self.device)
        return batch_tensor

    def __compute_phash_tensor(self, images: torch.Tensor) -> List[str]:
        dct_coeffs = self.__batch_dct2d(images)

        top_left = dct_coeffs[:, :, :self.hash_size, :self.hash_size]

        top_left_flat = top_left.reshape(top_left.size(0), -1)

        median_vals = torch.median(top_left_flat, dim=1, keepdim=True)[0]

        hash_bits = (top_left_flat > median_vals).long()

        hashes = []
        for bits in hash_bits:
            hash_int = 0
            for i, bit in enumerate(bits):
                if bit:
                    hash_int |= (1 << i)
            hash_hex = f"{hash_int:016x}"
            hashes.append(hash_hex)

        return hashes

    # noinspection PyPep8Naming
    def __batch_dct2d(self, images: torch.Tensor) -> torch.Tensor:
        N, C, H, W = images.shape  # pylint: disable=unused-variable

        if H != W or H != self.resize_size:
            images = F.interpolate(images, size=(self.resize_size, self.resize_size), mode='bilinear', align_corners=False)

        freq_h = torch.fft.fft(images, dim=2)
        freq_hw = torch.fft.fft(freq_h, dim=3)

        dct_coeffs = freq_hw.real

        return dct_coeffs
