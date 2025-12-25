from abc import (
    ABC,
    abstractmethod,
)
import logging
from typing import (
    Any,
    Dict,
    Optional,
)

from preprocessor.core.state_manager import StateManager
from preprocessor.utils.error_handling_logger import ErrorHandlingLogger


class BaseProcessor(ABC):
    def __init__(
        self,
        args: Dict[str, Any],
        class_name: str,
        error_exit_code: int,
        loglevel: int = logging.DEBUG,
    ):
        self._validate_args(args)
        self._args = args

        self.logger = ErrorHandlingLogger(
            class_name=class_name,
            loglevel=loglevel,
            error_exit_code=error_exit_code,
        )

        self.state_manager: Optional[StateManager] = args.get("state_manager")
        self.series_name: str = args.get("series_name", "unknown")

    @abstractmethod
    def _validate_args(self, args: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def _execute(self) -> None:
        pass

    def work(self) -> int:
        try:
            self._execute()
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error(f"{self.__class__.__name__} failed: {e}")
        return self.logger.finalize()

    def cleanup(self) -> None:
        pass
