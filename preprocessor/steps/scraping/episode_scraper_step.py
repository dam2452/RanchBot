from typing import Type

from preprocessor.config.step_configs import EpisodeScraperConfig
from preprocessor.services.scraping.base_scraper_step import BaseScraperStep
from preprocessor.services.scraping.episode_scraper import EpisodeScraper


class EpisodeScraperStep(BaseScraperStep[EpisodeScraperConfig]):
    def _get_scraper_class(self) -> Type[EpisodeScraper]:
        return EpisodeScraper

    def _get_metadata_type_name(self) -> str:
        return "Episodes"
