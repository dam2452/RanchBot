from typing import (
    List,
    Optional,
)

from PIL import Image
import torch
from torch import nn
import torch.nn.functional as F
from torchvision import (
    models,
    transforms,
)
from torchvision.models import ResNet18_Weights


class PerceptualHasher:

    def __init__(self, device: str = 'cuda', hash_size: int = 8) -> None:
        self.__device = device
        self.__hash_size = hash_size
        base_model = models.resnet18(weights=ResNet18_Weights.DEFAULT)
        self.model: Optional[nn.Module] = nn.Sequential(*list(base_model.children())[:-1])
        self.model.eval()
        if device == 'cuda' and torch.cuda.is_available():
            self.model = self.model.cuda()
        self.__transform = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

    def cleanup(self) -> None:
        if self.model is not None:
            del self.model
            self.model = None
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def compute_phash_batch(self, images: List[Image.Image]) -> List[str]:
        if self.model is None:
            raise RuntimeError('Model not initialized or already cleaned up')

        hashes: List[str] = []
        batch_tensors: List[torch.Tensor] = []

        for img in images:
            tensor = self.__transform(img)
            batch_tensors.append(tensor)

        if batch_tensors:
            batch = torch.stack(batch_tensors)
            if self.__device == 'cuda' and torch.cuda.is_available():
                batch = batch.cuda()

            with torch.no_grad():
                features = self.model(batch)
                features = F.adaptive_avg_pool2d(features, (1, 1))
                features = features.view(features.size(0), -1)

                for feature_vec in features:
                    hash_bits = (feature_vec > feature_vec.median()).int()
                    hash_str = ''.join([str(bit.item()) for bit in hash_bits[:self.__hash_size * self.__hash_size]])
                    hashes.append(hash_str)

        return hashes

    def __compute_hash(self, image_tensor: torch.Tensor) -> int:  # pylint: disable=unused-private-member
        if self.model is None:
            raise RuntimeError('Model not initialized or already cleaned up')
        with torch.no_grad():
            features = self.model(image_tensor)
            features = F.adaptive_avg_pool2d(features, (1, 1))
            features = features.flatten()
            hash_bits = (features > features.median()).int()
            hash_val = int(''.join([str(bit.item()) for bit in hash_bits.tolist()[:64]]), 2)
            return hash_val

__all__ = ['PerceptualHasher']
