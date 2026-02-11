from typing import (
    List,
    Union,
)

from preprocessor.lib.search.clients.embedding_service import EmbeddingService


class EmbeddingModelWrapper:

    def __init__(self, model_name: str, device: str='cuda', batch_size: int=8) -> None:
        self.model_name: str = model_name
        self.device: str = device
        self.batch_size: int = batch_size
        self._service = EmbeddingService()

    def encode_text(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        if isinstance(text, str):
            return self._service.get_text_embedding(text)
        return [self._service.get_text_embedding(t) for t in text]

    def __encode_image(self, image_path: str) -> List[float]: # pylint: disable=unused-private-member
        return self._service.get_image_embedding(image_path)
