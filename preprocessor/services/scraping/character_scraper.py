from typing import (
    Any,
    Dict,
    List,
)

from preprocessor.services.scraping.base_scraper import BaseScraper
from preprocessor.services.ui.console import console


class CharacterScraper(BaseScraper):
    def __init__(self, args: Dict[str, Any]) -> None:
        super().__init__(args)
        self.__series_name: str = self._args.get('series_name', '')

    def _process_scraped_pages(self, scraped_pages: List[Dict[str, Any]]) -> None:
        characters = self.llm.extract_characters(scraped_pages, self.__series_name)

        if not characters:
            self.logger.error('LLM failed to extract any character data')
            return

        payload = {
            'sources': [p['url'] for p in scraped_pages],
            'characters': [c.model_dump() for c in characters],
        }

        self._save_result(payload)
        console.print(f'[green]Extracted {len(characters)} characters. Saved to: {self.output_file}[/green]')
