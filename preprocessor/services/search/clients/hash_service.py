from pathlib import Path
from typing import (
    Optional,
    Union,
)

from PIL import Image
import click
import torch

from preprocessor.services.video.image_hasher import PerceptualHasher


class HashService:
    def __init__(self) -> None:
        self.__hasher: Optional[PerceptualHasher] = None

    def get_perceptual_hash(self, image_path: Union[str, Path]) -> Optional[str]:
        hasher = self.__get_hasher()
        with Image.open(image_path) as img:
            rgb_img = img.convert('RGB')
            hashes = hasher.compute_phash_batch([rgb_img])
        return hashes[0] if hashes else None

    def __get_hasher(self) -> PerceptualHasher:
        if self.__hasher is None:
            click.echo('Loading perceptual hasher...', err=True)
            self.__hasher = PerceptualHasher(device='cuda', hash_size=8)
        return self.__hasher

    def cleanup(self) -> None:
        if self.__hasher:
            self.__hasher = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
