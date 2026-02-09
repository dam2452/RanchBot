from pathlib import Path
from typing import (
    Optional,
    Union,
)

from PIL import Image
import click
import torch

from preprocessor.utils.image_hasher import PerceptualHasher


class HashService:
    def __init__(self) -> None:
        self._hasher: Optional[PerceptualHasher] = None

    def _load_hasher(self) -> PerceptualHasher:
        if self._hasher is not None:
            return self._hasher

        click.echo("Loading perceptual hasher...", err=True)
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is required but not available. This pipeline requires GPU.")

        self._hasher = PerceptualHasher(device="cuda", hash_size=8)
        click.echo("Hasher loaded on cuda", err=True)
        return self._hasher

    def get_perceptual_hash(self, image_path: Union[str, Path]) -> Optional[str]:
        hasher = self._load_hasher()
        image = Image.open(image_path).convert("RGB")
        hashes = hasher.compute_phash_batch([image])
        return hashes[0] if hashes else None

    def cleanup(self) -> None:
        if self._hasher is not None:
            del self._hasher
            self._hasher = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
