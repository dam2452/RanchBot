from typing import (
    List,
    Union,
)

import numpy as np

from preprocessor.services.search.clients.embedding_service import EmbeddingService


class EmbeddingModelWrapper:
    def __init__(
            self,
            model_name: str,
            device: str = 'cuda',
            batch_size: int = 8,
    ) -> None:
        self.__model_name = model_name  # pylint: disable=unused-private-member
        self.__device = device  # pylint: disable=unused-private-member
        self.__batch_size = batch_size  # pylint: disable=unused-private-member
        self.__service = EmbeddingService()
        self.__loaded = False  # pylint: disable=unused-private-member

    def load_model(self) -> None:
        self.__loaded = True  # pylint: disable=unused-private-member

    def cleanup(self) -> None:
        self.__loaded = False  # pylint: disable=unused-private-member

    def encode_text(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        if isinstance(text, str):
            return self.__service.get_text_embedding(text)

        return self.__process_batch_encoding(text)

    def encode_images(self, image_paths: List[str]) -> List[np.ndarray]:
        embeddings: List[np.ndarray] = []
        for path in image_paths:
            embedding = self.__service.get_image_embedding(path)
            embeddings.append(np.array(embedding))
        return embeddings

    def __process_batch_encoding(self, texts: List[str]) -> List[List[float]]:
        return [self.__service.get_text_embedding(t) for t in texts]
