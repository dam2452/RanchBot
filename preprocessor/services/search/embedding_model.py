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
            _batch_size: int = 8,
    ) -> None:
        self.__service = EmbeddingService(model_name=model_name, device=device)

    def load_model(self) -> None:
        self.__service.ensure_loaded()

    def cleanup(self) -> None:
        self.__service.cleanup()

    def encode_text(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        if isinstance(text, str):
            return self.__service.get_text_embeddings_batch([text])[0]
        return self.__service.get_text_embeddings_batch(text)

    def encode_images(self, image_paths: List[str]) -> List[np.ndarray]:
        embeddings_list = self.__service.get_image_embeddings_batch(image_paths)
        return [np.array(e) for e in embeddings_list]
