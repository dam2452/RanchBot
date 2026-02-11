from abc import (
    ABC,
    abstractmethod,
)
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Generic,
    TypeVar,
)

from pydantic import BaseModel

if TYPE_CHECKING:
    from preprocessor.core.context import ExecutionContext

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")
ConfigT = TypeVar("ConfigT", bound=BaseModel)


class PipelineStep(ABC, Generic[InputT, OutputT, ConfigT]):
    def __init__(self, config: ConfigT) -> None:
        self._config: ConfigT = config

    def cleanup(self) -> None:
        pass

    @property
    def config(self) -> ConfigT:
        return self._config

    @abstractmethod
    def execute(self, input_data: InputT, context: "ExecutionContext") -> OutputT:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    def _check_cache_validity(
        self,
        output_path: Path,
        context: "ExecutionContext",
        episode_id: str,
        cache_description: str,
    ) -> bool:
        if output_path.exists() and (not context.force_rerun):
            if context.is_step_completed(self.name, episode_id):
                context.logger.info(f'Skipping {episode_id} ({cache_description})')
                return True
        return False
