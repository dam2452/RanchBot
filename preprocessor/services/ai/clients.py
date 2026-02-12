from abc import (
    ABC,
    abstractmethod,
)
from typing import (
    Dict,
    List,
    Optional,
)

from openai import OpenAI
from vllm import (
    LLM,
    SamplingParams,
)

from preprocessor.config.config import settings
from preprocessor.services.ui.console import console


class BaseLLMClient(ABC):
    @abstractmethod
    def generate(self, messages: List[Dict[str, str]], max_tokens: int = 32768) -> str:
        pass


class VLLMClient(BaseLLMClient):
    __DEFAULT_MODEL_NAME = 'Qwen/Qwen2.5-Coder-7B-Instruct'

    def __init__(self, model_name: Optional[str] = None) -> None:
        self._model_name = model_name or self.__DEFAULT_MODEL_NAME
        self._model: Optional[LLM] = None
        self.__load_model()

    def generate(self, messages: List[Dict[str, str]], max_tokens: int = 32768) -> str:
        if self._model is None:
            raise RuntimeError('Model not initialized')

        sampling_params = SamplingParams(
            temperature=0.7,
            top_p=0.8,
            top_k=20,
            max_tokens=max_tokens,
            repetition_penalty=1.05,
        )
        outputs = self._model.chat(messages=[messages], sampling_params=sampling_params)
        return outputs[0].outputs[0].text.strip()

    def __load_model(self) -> None:
        console.print(f'[cyan]Loading LLM: {self._model_name} (vLLM, 128K context)[/cyan]')
        try:
            self._model = LLM(
                model=self._model_name,
                trust_remote_code=True,
                max_model_len=131072,
                gpu_memory_utilization=0.95,
                tensor_parallel_size=1,
                dtype='bfloat16',
                enable_chunked_prefill=True,
                max_num_batched_tokens=16384,
                enforce_eager=True,
                disable_log_stats=True,
            )
            console.print('[green]LLM loaded successfully (vLLM)[/green]')
        except Exception as e:
            console.print(f'[red]Failed to load model: {e}[/red]')
            raise


class GeminiClient(BaseLLMClient):
    __GEMINI_MODEL_NAME = 'gemini-2.5-flash'

    def __init__(self) -> None:
        self._client: Optional[OpenAI] = None
        self.__init_client()

    def generate(self, messages: List[Dict[str, str]], max_tokens: int = 32768) -> str:
        if self._client is None:
            raise RuntimeError('Gemini client not initialized')

        response = self._client.chat.completions.create(
            model=self.__GEMINI_MODEL_NAME,
            messages=messages,
        )
        return response.choices[0].message.content.strip()

    def __init_client(self) -> None:
        console.print('[cyan]Initializing Gemini 2.5 Flash via OpenAI SDK...[/cyan]')
        try:
            api_key = settings.gemini.api_key
            if not api_key:
                raise ValueError('GEMINI_API_KEY not set in environment')
            self._client = OpenAI(
                base_url='https://generativelanguage.googleapis.com/v1beta/openai/',
                api_key=api_key,
            )
            console.print('[green]Gemini 2.5 Flash initialized[/green]')
        except Exception as e:
            console.print(f'[red]Failed to initialize Gemini client: {e}[/red]')
            raise
