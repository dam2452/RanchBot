import json
from typing import (
    Any,
    Dict,
    List,
)

from preprocessor.scraping.base_scraper import BaseScraper
from preprocessor.utils.console import console


class CharacterScraper(BaseScraper):
    def __init__(self, args: Dict[str, Any]):
        super().__init__(args)
        self.series_name: str = self._args.get("series_name", "")

    def _process_scraped_pages(self, scraped_pages: List[Dict[str, Any]]) -> None:
        characters = self.llm.extract_characters(scraped_pages, self.series_name)
        if not characters:
            self.logger.error("LLM failed to extract any character data")
            return

        result = {
            "sources": [item["url"] for item in scraped_pages],
            "characters": [char.model_dump() for char in characters],
        }

        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        console.print(f"[green]✓ Extracted {len(characters)} characters[/green]")
        console.print(f"[green]✓ Saved to: {self.output_file}[/green]")
