from abc import (
    ABC,
    abstractmethod,
)
from pathlib import Path
from typing import (
    Any,
    Dict,
    Optional,
    TypeVar,
)

from pydantic import BaseModel

from preprocessor.core.artifacts import SourceVideo
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext

ConfigT = TypeVar("ConfigT", bound=BaseModel)


class BaseScraperStep(PipelineStep[SourceVideo, SourceVideo, ConfigT], ABC):

    def __init__(self, config: ConfigT) -> None:
        super().__init__(config)
        self._executed = False

    def execute(
        self, input_data: SourceVideo, context: ExecutionContext,
    ) -> Optional[SourceVideo]:
        if self._executed:
            return input_data

        output_path = Path(self.config.output_file)  # type: ignore[attr-defined]

        if output_path.exists() and not context.force_rerun:
            context.logger.info(f"{self._get_metadata_type_name()} metadata already exists: {output_path}")
            self._executed = True
            return input_data

        urls = self.config.urls  # type: ignore[attr-defined]
        context.logger.info(f"Scraping {self._get_metadata_type_name().lower()} from {len(urls)} URLs")

        scraper_class = self._get_scraper_class()
        scraper_args = self._build_scraper_args(output_path, context)
        scraper = scraper_class(scraper_args)

        exit_code = scraper.work()

        if exit_code != 0:
            raise RuntimeError(f"{self._get_metadata_type_name()} scraper failed with exit code {exit_code}")

        context.logger.info(f"{self._get_metadata_type_name()} metadata saved to: {output_path}")

        self._executed = True
        return input_data

    @abstractmethod
    def _get_scraper_class(self):
        pass

    @abstractmethod
    def _get_metadata_type_name(self) -> str:
        pass

    def _build_scraper_args(self, output_path: Path, context: ExecutionContext) -> Dict[str, Any]:
        base_args: Dict[str, Any] = {
            "urls": self.config.urls,  # type: ignore[attr-defined]
            "output_file": output_path,
            "headless": self.config.headless,  # type: ignore[attr-defined]
            "scraper_method": self.config.scraper_method,  # type: ignore[attr-defined]
            "parser_mode": self.config.parser_mode,  # type: ignore[attr-defined]
            "series_name": context.series_name,
        }
        return base_args
