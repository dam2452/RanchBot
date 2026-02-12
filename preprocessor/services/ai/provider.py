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
    SeasonMetadata,
)
from preprocessor.services.ui.console import console


class LLMProvider:

    def __init__(self, model_name: Optional[str] = None, parser_mode: Optional[ParserMode] = None) -> None:
        self._parser_mode = parser_mode or ParserMode.NORMAL

        if self._parser_mode == ParserMode.PREMIUM:
            self._client: BaseLLMClient = GeminiClient()
        else:
            self._client: BaseLLMClient = VLLMClient(model_name=model_name)

    def extract_all_seasons(self, scraped_pages: List[Dict[str, Any]]) -> Optional[List[SeasonMetadata]]:
        combined_content = self.__build_combined_content(scraped_pages)

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
        combined_content = self.__build_combined_content(scraped_pages)

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

    @staticmethod
    def __build_combined_content(scraped_pages: List[Dict[str, Any]]) -> str:
        """Build combined markdown from scraped pages.

        Args:
            scraped_pages: List of scraped page dictionaries with 'url' and 'markdown' keys.

        Returns:
            Combined content with source separators.
        """
        combined_parts: List[str] = []
        for i, page in enumerate(scraped_pages, 1):
            url: str = page['url']
            markdown: str = page['markdown']
            combined_parts.append(
                f'\n\n=== SOURCE {i}: {url} ===\n\n{markdown}\n',
            )
        return ''.join(combined_parts)

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

    def __process_llm_request(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[BaseModel],
        error_context: str,
    ) -> Optional[BaseModel]:
        try:
            messages = [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ]
            content = self._client.generate(messages)
            data = self.__extract_json(content)
            return response_model(**data)
        except Exception as e:
            console.print(f'[red]LLM {error_context}: {e}[/red]')
            return None
