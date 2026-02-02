import json
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Type,
)

from openai import OpenAI
from pydantic import (
    BaseModel,
    field_validator,
    model_validator,
)
from vllm import (
    LLM,
    SamplingParams,
)

from preprocessor.config.config import settings
from preprocessor.core.enums import ParserMode
from preprocessor.prompts import (
    extract_all_seasons_system,
    extract_all_seasons_user,
    extract_characters_system,
    extract_characters_user,
    extract_episode_metadata_system,
    extract_episode_metadata_user,
    extract_season_system,
    extract_season_user,
    merge_episode_data_system,
    merge_episode_data_user,
)
from preprocessor.utils.console import console


class EpisodeInfo(BaseModel):
    episode_in_season: int
    overall_episode_number: int
    title: str
    premiere_date: Optional[str] = None
    viewership: Optional[str] = None

    @field_validator('viewership', mode='before')
    @classmethod
    def convert_viewership_to_str(cls, v):
        if v is None:
            return None
        if isinstance(v, int):
            return str(v)
        return v


class SeasonMetadata(BaseModel):
    season_number: int
    episodes: List[EpisodeInfo]

    @model_validator(mode='before')
    @classmethod
    def convert_old_format(cls, data):
        if isinstance(data, dict) and 'episodes' in data:
            for idx, episode in enumerate(data['episodes'], start=1):
                if isinstance(episode, dict) and 'episode_number' in episode and 'episode_in_season' not in episode:
                    episode['episode_in_season'] = idx
                    episode['overall_episode_number'] = episode['episode_number']
                    del episode['episode_number']
        return data


class AllSeasonsMetadata(BaseModel):
    seasons: List[SeasonMetadata]


class EpisodeMetadata(BaseModel):
    title: str
    description: str
    summary: str
    season: Optional[int] = None
    episode_number: Optional[int] = None


class CharacterInfo(BaseModel):
    name: str


class CharactersList(BaseModel):
    characters: List[CharacterInfo]


class LLMProvider:
    __DEFAULT_MODEL_NAME = "Qwen/Qwen2.5-Coder-7B-Instruct"
    __GEMINI_MODEL_NAME = "gemini-2.5-flash"

    __instance = None
    __model = None
    __openai_client = None

    def __new__(cls, model_name: Optional[str] = None, parser_mode: Optional[ParserMode] = None):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance

    def __init__(self, model_name: Optional[str] = None, parser_mode: Optional[ParserMode] = None):
        self.parser_mode = parser_mode or ParserMode.NORMAL

        if self.parser_mode == ParserMode.PREMIUM:
            if self.__openai_client is None:
                self.__init_gemini_client()
        elif self.__model is None:
            self.model_name = model_name or self.__DEFAULT_MODEL_NAME
            self.__load_model()

    def extract_season_episodes(self, page_text: str, url: str) -> Optional[SeasonMetadata]:
        return self.__process_llm_request(
            system_prompt=extract_season_system.get(),
            user_prompt=extract_season_user.get().format(url=url, page_text=page_text),
            response_model=SeasonMetadata,
            error_context=f"extraction failed for {url}",
        )

    def extract_episode_metadata(self, page_text: str, url: str) -> Optional[EpisodeMetadata]:
        return self.__process_llm_request(
            system_prompt=extract_episode_metadata_system.get(),
            user_prompt=extract_episode_metadata_user.get().format(url=url, page_text=page_text),
            response_model=EpisodeMetadata,
            error_context=f"extraction failed for {url}",
        )

    def merge_episode_data(self, metadata_list: List[EpisodeMetadata]) -> EpisodeMetadata:
        if not metadata_list:
            raise ValueError("No metadata to merge")

        if len(metadata_list) == 1:
            return metadata_list[0]

        combined_text = "\n\n---\n\n".join([
            f"Source {i + 1}:\nTitle: {m.title}\nDescription: {m.description}\nSummary: {m.summary}\nSeason: {m.season}\nEpisode: {m.episode_number}"
            for i, m in enumerate(metadata_list)
        ])

        result = self.__process_llm_request(
            system_prompt=merge_episode_data_system.get(),
            user_prompt=merge_episode_data_user.get().format(
                num_sources=len(metadata_list),
                combined_text=combined_text,
            ),
            response_model=EpisodeMetadata,
            error_context="merge failed",
        )

        return result if result else metadata_list[0]

    def extract_all_seasons(self, scraped_pages: List[Dict[str, Any]]) -> Optional[List[SeasonMetadata]]:
        combined_content = ""
        for i, page in enumerate(scraped_pages, 1):
            url = page["url"]
            markdown = page["markdown"]
            combined_content += f"\n\n=== SOURCE {i}: {url} ===\n\n{markdown}\n"

        result = self.__process_llm_request(
            system_prompt=extract_all_seasons_system.get(),
            user_prompt=extract_all_seasons_user.get().format(
                num_sources=len(scraped_pages),
                combined_content=combined_content,
            ),
            response_model=AllSeasonsMetadata,
            error_context="extraction failed",
        )

        return result.seasons if result else None

    def extract_characters(self, scraped_pages: List[Dict[str, Any]], series_name: str) -> Optional[List[CharacterInfo]]:
        combined_content = ""
        for i, page in enumerate(scraped_pages, 1):
            url = page["url"]
            markdown = page["markdown"]
            combined_content += f"\n\n=== SOURCE {i}: {url} ===\n\n{markdown}\n"

        result = self.__process_llm_request(
            system_prompt=extract_characters_system.get(),
            user_prompt=extract_characters_user.get().format(
                num_sources=len(scraped_pages),
                series_name=series_name,
                combined_content=combined_content,
            ),
            response_model=CharactersList,
            error_context="character extraction failed",
        )

        return result.characters if result else None

    def __process_llm_request(
            self,
            system_prompt: str,
            user_prompt: str,
            response_model: Type[BaseModel],
            error_context: str,
    ) -> Optional[BaseModel]:
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            if self.parser_mode == ParserMode.PREMIUM:
                content = self.__generate_with_gemini(messages)
            else:
                content = self.__generate(messages)

            data = self.__extract_json(content)
            return response_model(**data)

        except Exception as e:
            console.print(f"[red]LLM {error_context}: {e}[/red]")
            return None

    def __init_gemini_client(self) -> None:
        console.print("[cyan]Initializing Gemini 2.5 Flash via OpenAI SDK...[/cyan]")
        try:
            api_key = settings.gemini.api_key
            if not api_key:
                raise ValueError("GEMINI_API_KEY not set in environment")

            self.__openai_client = OpenAI(
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                api_key=api_key,
            )
            console.print("[green]✓ Gemini 2.5 Flash initialized[/green]")
        except Exception as e:
            console.print(f"[red]Failed to initialize Gemini client: {e}[/red]")
            raise e

    def __load_model(self) -> None:
        console.print(f"[cyan]Loading LLM: {self.model_name} (vLLM, 128K context)[/cyan]")
        try:
            self.__model = LLM(
                model=self.model_name,
                trust_remote_code=True,
                max_model_len=131072,
                gpu_memory_utilization=0.95,
                tensor_parallel_size=1,
                dtype="bfloat16",
                enable_chunked_prefill=True,
                max_num_batched_tokens=16384,
                enforce_eager=True,
                disable_log_stats=True,
            )
            console.print("[green]✓ LLM loaded successfully (vLLM)[/green]")
        except Exception as e:
            console.print(f"[red]Failed to load model: {e}[/red]")
            raise e

    def __generate(self, messages: List[Dict], max_tokens: int = 32768) -> str:
        sampling_params = SamplingParams(
            temperature=0.7,
            top_p=0.8,
            top_k=20,
            max_tokens=max_tokens,
            repetition_penalty=1.05,
        )

        outputs = self.__model.chat(
            messages=[messages],
            sampling_params=sampling_params,
        )

        return outputs[0].outputs[0].text.strip()

    def __generate_with_gemini(self, messages: List[Dict]) -> str:
        response = self.__openai_client.chat.completions.create(
            model=self.__GEMINI_MODEL_NAME,
            messages=messages,
        )
        return response.choices[0].message.content.strip()

    @staticmethod
    def __extract_json(content: str) -> Dict:
        try:
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                json_str = content[start:end].strip()
            elif "```" in content:
                start = content.find("```") + 3
                end = content.find("```", start)
                json_str = content[start:end].strip()
            else:
                json_str = content.strip()

            return json.loads(json_str)
        except json.JSONDecodeError as e:
            console.print(f"[red]JSON parse error: {e}[/red]")
            console.print(f"[yellow]Raw content:\n{content}[/yellow]")
            raise
