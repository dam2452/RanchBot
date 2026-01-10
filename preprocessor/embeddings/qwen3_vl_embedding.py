import logging
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from PIL import Image
import torch
import torch.nn.functional as F
from vllm import LLM

from preprocessor.config.config import settings

logger = logging.getLogger(__name__)


class Qwen3VLEmbedder:
    def __init__(
        self,
        model_name_or_path: str,
        max_length: Optional[int] = None,
        tensor_parallel_size: Optional[int] = None,
        gpu_memory_utilization: Optional[float] = None,
        **kwargs,
    ):
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is required but not available. This pipeline requires GPU.")

        self.max_length = max_length or settings.embedding.max_model_len
        self.model_name_or_path = model_name_or_path
        self.image_placeholder = settings.embedding.image_placeholder

        dtype = kwargs.pop("torch_dtype", torch.bfloat16)
        dtype_str = "bfloat16" if dtype == torch.bfloat16 else "float16"

        self.model = LLM(
            model=model_name_or_path,
            runner="pooling",
            dtype=dtype_str,
            trust_remote_code=True,
            max_model_len=self.max_length,
            gpu_memory_utilization=gpu_memory_utilization or settings.embedding.gpu_memory_utilization,
            tensor_parallel_size=tensor_parallel_size or settings.embedding.tensor_parallel_size,
            enable_chunked_prefill=settings.embedding.enable_chunked_prefill,
            max_num_batched_tokens=settings.embedding.max_num_batched_tokens,
            enforce_eager=settings.embedding.enforce_eager,
            disable_log_stats=True,
        )

        logger.info(f"vLLM Qwen3-VL-Embedding loaded: {model_name_or_path}")

    def process(self, inputs: List[Dict[str, Any]], normalize: bool = True) -> torch.Tensor:
        vllm_inputs = []

        for item in inputs:
            text = item.get("text")
            image = item.get("image")
            video = item.get("video")

            if image:
                if isinstance(image, str):
                    img = Image.open(image).convert("RGB")
                elif isinstance(image, Image.Image):
                    img = image
                else:
                    raise TypeError(f"Unsupported image type: {type(image)}")

                vllm_inputs.append({
                    "prompt": self.image_placeholder,
                    "multi_modal_data": {"image": img},
                })
            elif text:
                vllm_inputs.append({
                    "prompt": text,
                })
            elif video:
                if isinstance(video, list):
                    frames = []
                    for frame in video:
                        if isinstance(frame, str):
                            frames.append(Image.open(frame).convert("RGB"))
                        elif isinstance(frame, Image.Image):
                            frames.append(frame)
                        else:
                            raise TypeError(f"Unsupported frame type: {type(frame)}")

                    vllm_inputs.append({
                        "prompt": self.image_placeholder,
                        "multi_modal_data": {"image": frames[0] if frames else None},
                    })
                else:
                    raise TypeError(f"Unsupported video type: {type(video)}")
            else:
                vllm_inputs.append({"prompt": "NULL"})

        outputs = self.model.embed(vllm_inputs)

        embeddings = torch.stack([
            torch.tensor(output.outputs.embedding, dtype=torch.float32)
            for output in outputs
        ])

        if normalize:
            embeddings = F.normalize(embeddings, p=2, dim=-1)

        return embeddings

    def get_text_embeddings(self, texts: List[str], normalize: bool = True) -> torch.Tensor:
        inputs = [{"text": text} for text in texts]
        return self.process(inputs, normalize=normalize)
