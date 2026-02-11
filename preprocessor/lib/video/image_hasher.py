from typing import Optional

import torch
from torch import nn
import torch.nn.functional as F
from torchvision import models
from torchvision.models import ResNet18_Weights


class PerceptualHasher:

    def __init__(self) -> None:
        base_model = models.resnet18(weights=ResNet18_Weights.DEFAULT)
        self.model: Optional[nn.Module] = nn.Sequential(*list(base_model.children())[:-1])
        self.model.eval()
        if torch.cuda.is_available():
            self.model = self.model.cuda()

    def cleanup(self) -> None:
        if self.model is not None:
            del self.model
            self.model = None
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def __compute_hash(self, image_tensor: torch.Tensor) -> int: # pylint: disable=unused-private-member
        if self.model is None:
            raise RuntimeError('Model not initialized or already cleaned up')
        with torch.no_grad():
            features = self.model(image_tensor)
            features = F.adaptive_avg_pool2d(features, (1, 1))
            features = features.flatten()
            hash_bits = (features > features.median()).int()
            hash_val = int(''.join([str(bit) for bit in hash_bits.tolist()[:64]]), 2)
            return hash_val
__all__ = ['PerceptualHasher']
