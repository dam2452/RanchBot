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
        self.series_name: str = self._args.get('series_name', '')

    def _process_scraped_pages(self, scraped_pages: List[Dict[str, Any]]) -> None:
        characters = self.llm.extract_characters(scraped_pages, self.series_name)
        if not characters:
            self.logger.error('LLM failed to extract any character data')
            return
        result = {'sources': [item['url'] for item in scraped_pages], 'characters': [char.model_dump() for char in characters]}
        self._save_result(result)
        console.print(f'[green]Extracted {len(characters)} characters[/green]')
        console.print(f'[green]Saved to: {self.output_file}[/green]')
