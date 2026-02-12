import json
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Type,
)

from pydantic import BaseModel

from preprocessor.config.enums import ParserMode
from preprocessor.config.prompts import (
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
from preprocessor.services.ai.clients import (
    BaseLLMClient,
    GeminiClient,
    VLLMClient,
)
from preprocessor.services.ai.models import (
    AllSeasonsMetadata,
    CharacterInfo,
    CharactersList,
    EpisodeMetadata,
    SeasonMetadata,
)
from preprocessor.services.ui.console import console


class LLMProvider:
    __client: Optional[BaseLLMClient] = None
    __instance: Optional['LLMProvider'] = None

    def __init__(self, model_name: Optional[str] = None, parser_mode: Optional[ParserMode] = None) -> None:
        self._parser_mode = parser_mode or ParserMode.NORMAL

        if self.__client is None:
            if self._parser_mode == ParserMode.PREMIUM:
                self.__client = GeminiClient()
            else:
                self.__client = VLLMClient(model_name=model_name)

    def extract_all_seasons(self, scraped_pages: List[Dict[str, Any]]) -> Optional[List[SeasonMetadata]]:
        combined_content = ''
        for i, page in enumerate(scraped_pages, 1):
            url = page['url']
            markdown = page['markdown']
            combined_content += f'\n\n=== SOURCE {i}: {url} ===\n\n{markdown}\n'

        result = self.__process_llm_request(
            system_prompt=extract_all_seasons_system.get(),
            user_prompt=extract_all_seasons_user.get().format(
                num_sources=len(scraped_pages),
                combined_content=combined_content,
            ),
            response_model=AllSeasonsMetadata,
            error_context='extraction failed',
        )
        return result.seasons if result else None

    def extract_characters(
        self,
        scraped_pages: List[Dict[str, Any]],
        series_name: str,
    ) -> Optional[List[CharacterInfo]]:
        combined_content = ''
        for i, page in enumerate(scraped_pages, 1):
            url = page['url']
            markdown = page['markdown']
            combined_content += f'\n\n=== SOURCE {i}: {url} ===\n\n{markdown}\n'

        result = self.__process_llm_request(
            system_prompt=extract_characters_system.get(),
            user_prompt=extract_characters_user.get().format(
                num_sources=len(scraped_pages),
                series_name=series_name,
                combined_content=combined_content,
            ),
            response_model=CharactersList,
            error_context='character extraction failed',
        )
        return result.characters if result else None

    def __new__(cls, model_name: Optional[str] = None, parser_mode: Optional[ParserMode] = None) -> 'LLMProvider':
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance

    def __extract_episode_metadata(self, page_text: str, url: str) -> Optional[EpisodeMetadata]:  # pylint: disable=unused-private-member
        return self.__process_llm_request(
            system_prompt=extract_episode_metadata_system.get(),
            user_prompt=extract_episode_metadata_user.get().format(url=url, page_text=page_text),
            response_model=EpisodeMetadata,
            error_context=f'extraction failed for {url}',
        )

    @staticmethod
    def __extract_json(content: str) -> Dict[str, Any]:
        try:
            if '```json' in content:
                start = content.find('```json') + 7
                end = content.find('```', start)
                json_str = content[start:end].strip()
            elif '```' in content:
                start = content.find('```') + 3
                end = content.find('```', start)
                json_str = content[start:end].strip()
            else:
                json_str = content.strip()
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            console.print(f'[red]JSON parse error: {e}[/red]')
            console.print(f'[yellow]Raw content:\n{content}[/yellow]')
            raise

    def __extract_season_episodes(self, page_text: str, url: str) -> Optional[SeasonMetadata]:  # pylint: disable=unused-private-member
        return self.__process_llm_request(
            system_prompt=extract_season_system.get(),
            user_prompt=extract_season_user.get().format(url=url, page_text=page_text),
            response_model=SeasonMetadata,
            error_context=f'extraction failed for {url}',
        )

    def __merge_episode_data(self, metadata_list: List[EpisodeMetadata]) -> EpisodeMetadata:  # pylint: disable=unused-private-member
        if not metadata_list:
            raise ValueError('No metadata to merge')
        if len(metadata_list) == 1:
            return metadata_list[0]

        combined_text = '\n\n---\n\n'.join([
            f'Source {i + 1}:\n'
            f'Title: {m.title}\n'
            f'Description: {m.description}\n'
            f'Summary: {m.summary}\n'
            f'Season: {m.season}\n'
            f'Episode: {m.episode_number}'
            for i, m in enumerate(metadata_list)
        ])

        result = self.__process_llm_request(
            system_prompt=merge_episode_data_system.get(),
            user_prompt=merge_episode_data_user.get().format(
                num_sources=len(metadata_list),
                combined_text=combined_text,
            ),
            response_model=EpisodeMetadata,
            error_context='merge failed',
        )
        return result if result else metadata_list[0]

    def __process_llm_request(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[BaseModel],
        error_context: str,
    ) -> Optional[BaseModel]:
        if self.__client is None:
            raise RuntimeError('LLM client not initialized')

        try:
            messages = [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ]
            content = self.__client.generate(messages)
            data = self.__extract_json(content)
            return response_model(**data)
        except Exception as e:
            console.print(f'[red]LLM {error_context}: {e}[/red]')
            return None
