from typing import Type

from preprocessor.config.step_configs import CharacterScraperConfig
from preprocessor.services.scraping.base_scraper_step import BaseScraperStep
from preprocessor.services.scraping.character_scraper import CharacterScraper


class CharacterScraperStep(BaseScraperStep[CharacterScraperConfig]):

    def _get_scraper_class(self) -> Type[CharacterScraper]:
        return CharacterScraper

    def _get_metadata_type_name(self) -> str:
        return "Characters"

    @property
    def name(self) -> str:
        return "scrape_characters"
