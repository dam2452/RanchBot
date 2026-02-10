from pathlib import Path
from typing import (
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

from preprocessor.config.config import settings


class EmbeddingService:

    def __init__(self) -> None:
        self._model: Optional[AutoModelForVision2Seq] = None
        self._processor: Optional[AutoProcessor] = None
        self._device: Optional[str] = None

    def _load_model(self) -> Tuple[AutoModelForVision2Seq, AutoProcessor, str]:
        if self._model is not None:
            return (self._model, self._processor, self._device)
        click.echo('Loading embedding model...', err=True)
        if not torch.cuda.is_available():
            raise RuntimeError('CUDA is required but not available. This pipeline requires GPU.')
        model_name = settings.embedding_model.model_name
        self._device = 'cuda'
        self._model = AutoModelForVision2Seq.from_pretrained(model_name, dtype=torch.bfloat16, device_map='auto')
        self._processor = AutoProcessor.from_pretrained(model_name)
        click.echo(f'Model loaded on {self._device}', err=True)
        return (self._model, self._processor, self._device)

    def get_text_embedding(self, text: str) -> List[float]:
        model, processor, device = self._load_model()
        messages = [{'role': 'user', 'content': [{'type': 'text', 'text': text}]}]
        text_inputs = processor.apply_chat_template(messages, add_generation_prompt=True, tokenize=True, return_tensors='pt').to(device)
        with torch.no_grad():
            output = model(input_ids=text_inputs, output_hidden_states=True)
            embedding = output.hidden_states[-1][:, -1, :].squeeze(0)
            embedding = torch.nn.functional.normalize(embedding, p=2, dim=0)
        return embedding.float().cpu().numpy().tolist()

    def get_image_embedding(self, image_path: Union[str, Path]) -> List[float]:
        model, processor, device = self._load_model()
        messages = [{'role': 'user', 'content': [{'type': 'image', 'image': str(image_path)}, {'type': 'text', 'text': 'Describe this image.'}]}]
        text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = processor(text=[text], images=image_inputs, videos=video_inputs, padding=True, return_tensors='pt')
        inputs = inputs.to(device)
        with torch.no_grad():
            output = model(**inputs, output_hidden_states=True)
            embedding = output.hidden_states[-1][:, -1, :].squeeze(0)
            embedding = torch.nn.functional.normalize(embedding, p=2, dim=0)
        return embedding.float().cpu().numpy().tolist()

    def cleanup(self) -> None:
        if self._model is not None:
            del self._model
            del self._processor
            self._model = None
            self._processor = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
