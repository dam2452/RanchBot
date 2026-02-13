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
    def __init__(self) -> None:
        self.__model: Optional[AutoModelForVision2Seq] = None
        self.__processor: Optional[AutoProcessor] = None
        self.__device: str = 'cuda'

    def cleanup(self) -> None:
        if self.__model is not None:
            del self.__model
            del self.__processor
            self.__model = self.__processor = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    def get_image_embedding(self, image_path: Union[str, Path]) -> List[float]:
        model, processor, device = self.__get_model()
        messages = [{
            'role': 'user', 'content': [
                {'type': 'image', 'image': str(image_path)},
                {'type': 'text', 'text': 'Describe this image.'},
            ],
        }]

        image_inputs, video_inputs = process_vision_info(messages)
        prompt = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

        inputs = processor(
            text=[prompt], images=image_inputs, videos=video_inputs, padding=True,
            return_tensors='pt',
        ).to(device)
        return self.__compute_normalized_embedding(model, inputs)

    def get_text_embedding(self, text: str) -> List[float]:
        model, processor, device = self.__get_model()
        messages = [{'role': 'user', 'content': [{'type': 'text', 'text': text}]}]

        inputs = processor.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=True,
            return_tensors='pt',
        ).to(device)
        return self.__compute_normalized_embedding(model, {'input_ids': inputs})

    def __compute_normalized_embedding(self, model: Any, inputs: Dict[str, Any]) -> List[float]:
        with torch.no_grad():
            output = model(**inputs, output_hidden_states=True)
            embedding = output.hidden_states[-1][:, -1, :].squeeze(0)
            embedding = torch.nn.functional.normalize(embedding, p=2, dim=0)
        return embedding.float().cpu().numpy().tolist()

    def __get_model(self) -> Tuple[AutoModelForVision2Seq, AutoProcessor, str]:
        if self.__model is None:
            self.__load_resources()
        return self.__model, self.__processor, self.__device

    def __load_resources(self) -> None:
        click.echo('Loading Qwen-VL embedding model...', err=True)
        if not torch.cuda.is_available():
            raise RuntimeError('CUDA required for multimodal embeddings.')

        model_name = settings.embedding_model.model_name
        self.__model = AutoModelForVision2Seq.from_pretrained(model_name, dtype=torch.bfloat16, device_map='auto')
        self.__processor = AutoProcessor.from_pretrained(model_name)
