from preprocessor.config.step_configs import CharacterScraperConfig
from preprocessor.modules.scraping.base_scraper_step import BaseScraperStep
from preprocessor.modules.scraping.character_scraper import CharacterScraper


class CharacterScraperStep(BaseScraperStep[CharacterScraperConfig]):

    def _get_scraper_class(self):
        return CharacterScraper

    def _get_metadata_type_name(self) -> str:
        return "Characters"

    @property
    def name(self) -> str:
        return "scrape_characters"
