import gc
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
)

import click
from qwen_vl_utils import process_vision_info
import torch
from transformers import (
    AutoModelForVision2Seq,
    AutoProcessor,
)

from preprocessor.config.settings_instance import settings


class EmbeddingService:
    def __init__(self, model_name: Optional[str] = None, device: str = 'cuda') -> None:
        self.__model_name: str = model_name or settings.embedding_model.model_name
        self.__device = device
        self.__model: Optional[AutoModelForVision2Seq] = None
        self.__processor: Optional[AutoProcessor] = None

    def ensure_loaded(self) -> None:
        if self.__model is None:
            self.__load_resources()

    def cleanup(self) -> None:
        if self.__model is not None:
            del self.__model
            del self.__processor
            self.__model = self.__processor = None
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    def get_image_embeddings_batch(self, image_paths: List[Union[str, Path]]) -> List[List[float]]:
        model, processor, device = self.__get_model()

        messages_batch = [
            [{
                'role': 'user', 'content': [
                    {'type': 'image', 'image': str(path)},
                    {'type': 'text', 'text': 'Describe this image.'},
                ],
            }]
            for path in image_paths
        ]

        all_image_inputs: List[Any] = []
        prompts: List[str] = []
        for messages in messages_batch:
            image_inputs, _ = process_vision_info(messages)
            all_image_inputs.extend(image_inputs)
            prompts.append(
                processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True),
            )

        inputs = processor(
            text=prompts,
            images=all_image_inputs,
            padding=True,
            return_tensors='pt',
        ).to(device)

        return self.__compute_batch_embeddings(model, inputs, len(image_paths))

    def get_text_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        model, processor, device = self.__get_model()

        messages_batch = [
            [{'role': 'user', 'content': [{'type': 'text', 'text': text}]}]
            for text in texts
        ]
        prompts: List[str] = [
            processor.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
            for msgs in messages_batch
        ]

        inputs = processor(
            text=prompts,
            padding=True,
            return_tensors='pt',
        ).to(device)

        return self.__compute_batch_embeddings(model, inputs, len(texts))

    @staticmethod
    def __compute_batch_embeddings(
        model: Any,
        inputs: Dict[str, Any],
        count: int,
    ) -> List[List[float]]:
        with torch.no_grad():
            output = model(**inputs, output_hidden_states=True)
            hidden = output.hidden_states[-1]

            attention_mask = inputs.get('attention_mask')
            if attention_mask is not None:
                last_positions = attention_mask.sum(dim=1) - 1
                embeddings = torch.stack([
                    hidden[i, last_positions[i], :] for i in range(count)
                ])
            else:
                embeddings = hidden[:, -1, :]

            embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=-1)

        result = [emb.float().cpu().numpy().tolist() for emb in embeddings]
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        return result

    def __get_model(self) -> Tuple[AutoModelForVision2Seq, AutoProcessor, str]:
        if self.__model is None:
            self.__load_resources()
        return self.__model, self.__processor, self.__device

    def __load_resources(self) -> None:
        click.echo('Loading Qwen-VL embedding model...', err=True)
        if not torch.cuda.is_available():
            raise RuntimeError('CUDA required for multimodal embeddings.')

        self.__model = AutoModelForVision2Seq.from_pretrained(
            self.__model_name, dtype=torch.bfloat16, device_map='auto',
        )
        self.__processor = AutoProcessor.from_pretrained(self.__model_name)
