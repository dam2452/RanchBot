import gc
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Union,
)

from PIL import Image
import click
import torch
from vllm import LLM

from preprocessor.config.settings_instance import settings


class EmbeddingService:
    def __init__(self, model_name: Optional[str] = None) -> None:
        self.__model_name: str = model_name or settings.embedding_model.model_name
        self.__llm: Optional[LLM] = None

    def ensure_loaded(self) -> None:
        if self.__llm is None:
            self.__load_resources()

    def cleanup(self) -> None:
        if self.__llm is not None:
            del self.__llm
            self.__llm = None
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    def get_image_embeddings_batch(self, image_paths: List[Union[str, Path]]) -> List[List[float]]:
        placeholder = settings.embedding_model.image_placeholder
        inputs: List[Dict[str, Any]] = [
            {
                'prompt': f'{placeholder}\nDescribe this image.',
                'multi_modal_data': {'image': Image.open(str(path)).convert('RGB')},
            }
            for path in image_paths
        ]
        return self.__embed(inputs)

    def get_text_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        inputs: List[Dict[str, Any]] = [{'prompt': text} for text in texts]
        return self.__embed(inputs)

    def __embed(self, inputs: List[Dict[str, Any]]) -> List[List[float]]:
        if self.__llm is None:
            self.__load_resources()
        outputs = self.__llm.encode(inputs)  # type: ignore[union-attr]
        return [output.outputs.embedding for output in outputs]

    def __load_resources(self) -> None:
        click.echo('Loading vLLM embedding model...', err=True)
        if not torch.cuda.is_available():
            raise RuntimeError('CUDA required for multimodal embeddings.')

        em = settings.embedding_model
        self.__llm = LLM(
            model=self.__model_name,
            max_model_len=em.max_model_len,
            gpu_memory_utilization=em.gpu_memory_utilization,
            enable_chunked_prefill=em.enable_chunked_prefill,
            enforce_eager=em.enforce_eager,
            max_num_batched_tokens=em.max_num_batched_tokens,
            tensor_parallel_size=em.tensor_parallel_size,
        )
