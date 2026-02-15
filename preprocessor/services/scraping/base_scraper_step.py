from abc import (
    ABC,
    abstractmethod,
)
from pathlib import Path
from typing import (
    Any,
    Dict,
    Optional,
    Type,
    TypeVar,
)

from pydantic import BaseModel

from preprocessor.config.output_paths import get_base_output_dir
from preprocessor.core.artifacts import SourceVideo
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext

ConfigT = TypeVar("ConfigT", bound=BaseModel)


class BaseScraperStep(PipelineStep[SourceVideo, SourceVideo, ConfigT], ABC):
    @property
    def is_global(self) -> bool:
        return True

    def execute(self, input_data: SourceVideo, context: ExecutionContext) -> Optional[SourceVideo]:
        output_path = self.__resolve_output_path(context)

        if output_path.exists() and not context.force_rerun:
            context.logger.info(f"{self._get_metadata_type_name()} metadata already exists.")
            return input_data

        context.logger.info(f"Scraping {self._get_metadata_type_name().lower()} from {len(self.config.urls)} URLs")

        scraper = self._get_scraper_class()(self._build_scraper_args(output_path, context))
        exit_code = scraper.work()

        if exit_code != 0:
            raise RuntimeError(f"{self._get_metadata_type_name()} scraper failed with code {exit_code}")

        context.logger.info(f"{self._get_metadata_type_name()} metadata saved to: {output_path}")
        return input_data

    def __resolve_output_path(self, context: ExecutionContext) -> Path:
        metadata_type = self._get_metadata_type_name().lower()
        output_dir = get_base_output_dir(context.series_name)
        return output_dir / f"{context.series_name}_{metadata_type}.json"

    @abstractmethod
    def _get_scraper_class(self) -> Type:
        pass

    @abstractmethod
    def _get_metadata_type_name(self) -> str:
        pass

    def _build_scraper_args(self, output_path: Path, context: ExecutionContext) -> Dict[str, Any]:
        return {
            "urls": self.config.urls,
            "output_file": output_path,
            "headless": self.config.headless,
            "scraper_method": self.config.scraper_method,
            "parser_mode": self.config.parser_mode,
            "series_name": context.series_name,
        }
