from abc import (
    ABC,
    abstractmethod,
)
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
