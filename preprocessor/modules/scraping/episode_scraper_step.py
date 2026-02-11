from pathlib import Path
from typing import Optional

from preprocessor.config.step_configs import EpisodeScraperConfig
from preprocessor.core.artifacts import SourceVideo
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.modules.scraping.episode_scraper import EpisodeScraper


class EpisodeScraperStep(
    PipelineStep[SourceVideo, SourceVideo, EpisodeScraperConfig],
):
    def __init__(self, config: EpisodeScraperConfig) -> None:
        super().__init__(config)
        self._executed = False

    @property
    def name(self) -> str:
        return "scrape_episodes"

    def execute(
        self, input_data: SourceVideo, context: ExecutionContext,
    ) -> Optional[SourceVideo]:
        if self._executed:
            return input_data

        output_path = Path(self.config.output_file)

        if output_path.exists() and not context.force_rerun:
            context.logger.info(f"Episodes metadata already exists: {output_path}")
            self._executed = True
            return input_data

        context.logger.info(f"Scraping episodes from {len(self.config.urls)} URLs")

        scraper = EpisodeScraper(
            {
                "urls": self.config.urls,
                "output_file": output_path,
                "headless": self.config.headless,
                "merge_sources": self.config.merge_sources,
                "scraper_method": self.config.scraper_method,
                "parser_mode": self.config.parser_mode,
                "series_name": context.series_name,
            },
        )

        exit_code = scraper.work()

        if exit_code != 0:
            raise RuntimeError(f"Episode scraper failed with exit code {exit_code}")

        context.logger.info(f"Episodes metadata saved to: {output_path}")

        self._executed = True
        return input_data
