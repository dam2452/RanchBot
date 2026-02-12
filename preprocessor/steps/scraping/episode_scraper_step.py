from pathlib import Path
from typing import (
    Any,
    Dict,
    Type,
)

from preprocessor.config.step_configs import EpisodeScraperConfig
from preprocessor.core.context import ExecutionContext
from preprocessor.services.scraping.base_scraper_step import BaseScraperStep
from preprocessor.services.scraping.episode_scraper import EpisodeScraper


class EpisodeScraperStep(BaseScraperStep[EpisodeScraperConfig]):

    def _get_scraper_class(self) -> Type[EpisodeScraper]:
        return EpisodeScraper

    def _get_metadata_type_name(self) -> str:
        return "Episodes"

    def _build_scraper_args(self, output_path: Path, context: ExecutionContext) -> Dict[str, Any]:
        args = super()._build_scraper_args(output_path, context)
        args["merge_sources"] = self.config.merge_sources
        return args

    @property
    def name(self) -> str:
        return "scrape_episodes"
