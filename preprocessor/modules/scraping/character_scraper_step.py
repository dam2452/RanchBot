from pathlib import Path
from typing import Optional

from preprocessor.config.step_configs import CharacterScraperConfig
from preprocessor.core.artifacts import SourceVideo
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.modules.scraping.character_scraper import CharacterScraper


class CharacterScraperStep(
    PipelineStep[SourceVideo, SourceVideo, CharacterScraperConfig],
):
    def __init__(self, config: CharacterScraperConfig) -> None:
        super().__init__(config)
        self._executed = False

    @property
    def name(self) -> str:
        return "scrape_characters"

    def execute(
        self, input_data: SourceVideo, context: ExecutionContext,
    ) -> Optional[SourceVideo]:
        if self._executed:
            return input_data

        output_path = Path(self.config.output_file)

        if output_path.exists() and not context.force_rerun:
            context.logger.info(f"Characters metadata already exists: {output_path}")
            self._executed = True
            return input_data

        context.logger.info(f"Scraping characters from {len(self.config.urls)} URLs")

        scraper = CharacterScraper(  # pylint: disable=abstract-class-instantiated
            {
                "urls": self.config.urls,
                "output_file": output_path,
                "headless": self.config.headless,
                "scraper_method": self.config.scraper_method,
                "parser_mode": self.config.parser_mode,
            },
        )

        exit_code = scraper.work()

        if exit_code != 0:
            raise RuntimeError(f"Character scraper failed with exit code {exit_code}")

        context.logger.info(f"Characters metadata saved to: {output_path}")

        self._executed = True
        return input_data
