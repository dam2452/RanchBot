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

from preprocessor.config.settings_instance import settings
from preprocessor.services.ui.console import console


class BaseLLMClient(ABC):
    @abstractmethod
    def generate(self, messages: List[Dict[str, str]], max_tokens: int = 32768) -> str:
        pass


class VLLMClient(BaseLLMClient):
    __DEFAULT_MODEL_NAME = 'Qwen/Qwen3.5-9B'

    def __init__(self, model_name: Optional[str] = None) -> None:
        self.__model_name = model_name or self.__DEFAULT_MODEL_NAME
        self.__model: Optional[LLM] = None
        self.__load_model()

    def generate(self, messages: List[Dict[str, str]], max_tokens: int = 32768) -> str:
        if self.__model is None:
            raise RuntimeError('Model not initialized')

        sampling_params = SamplingParams(
            temperature=1.0,
            top_p=0.95,
            top_k=20,
            min_p=0.0,
            presence_penalty=1.5,
            repetition_penalty=1.0,
            max_tokens=max_tokens,
        )
        outputs = self.__model.chat(
            messages=[messages],
            sampling_params=sampling_params,
            chat_template_kwargs={'enable_thinking': False},
        )
        return outputs[0].outputs[0].text.strip()

    def __load_model(self) -> None:
        console.print(f'[cyan]Loading LLM: {self.__model_name} (vLLM, 256K context)[/cyan]')
        try:
            self.__model = LLM(
                model=self.__model_name,
                trust_remote_code=True,
                max_model_len=262144,
                gpu_memory_utilization=0.90,
                tensor_parallel_size=1,
                dtype='bfloat16',
                enable_chunked_prefill=True,
                max_num_batched_tokens=16384,
                enforce_eager=True,
                disable_log_stats=True,
                language_model_only=True,
            )
            console.print('[green]LLM loaded successfully (vLLM)[/green]')
        except Exception as e:
            console.print(f'[red]Failed to load model: {e}[/red]')
            raise


class GeminiClient(BaseLLMClient):
    def __init__(
        self,
        model_name: str = 'gemini-2.5-flash',
        base_url: str = 'https://generativelanguage.googleapis.com/v1beta/openai/',
        api_key: Optional[str] = None,
    ) -> None:
        self.__model_name = model_name
        self.__base_url = base_url
        self.__api_key = api_key or settings.gemini.api_key
        self.__client: Optional[OpenAI] = None
        self.__init_client()

    def generate(self, messages: List[Dict[str, str]], max_tokens: int = 32768) -> str:
        if self.__client is None:
            raise RuntimeError('Gemini client not initialized')

        response = self.__client.chat.completions.create(
            model=self.__model_name,
            messages=messages,  # type: ignore[arg-type]
        )
        return response.choices[0].message.content.strip()

    def __init_client(self) -> None:
        console.print(f'[cyan]Initializing {self.__model_name} via OpenAI SDK...[/cyan]')
        try:
            if not self.__api_key:
                raise ValueError('GEMINI_API_KEY not set in environment')

            self.__client = OpenAI(
                base_url=self.__base_url,
                api_key=self.__api_key,
            )
            console.print(f'[green]{self.__model_name} initialized[/green]')
        except Exception as e:
            console.print(f'[red]Failed to initialize Gemini client: {e}[/red]')
            raise
