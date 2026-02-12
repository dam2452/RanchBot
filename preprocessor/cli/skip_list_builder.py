from typing import (
    List,
    Tuple,
)

from preprocessor.config.series_config import SeriesConfig
from preprocessor.services.core.logging import ErrorHandlingLogger


class SkipListBuilder:
    @staticmethod
    def build(
        cli_skip: Tuple[str, ...],
        series_config: SeriesConfig,
        logger: ErrorHandlingLogger,
    ) -> List[str]:
        skip_list = list(cli_skip)
        if series_config.pipeline_mode == "selective" and series_config.skip_steps:
            logger.info(f"Selective mode: auto-skipping {', '.join(series_config.skip_steps)}")
            skip_list.extend(series_config.skip_steps)
        return list(set(skip_list))
