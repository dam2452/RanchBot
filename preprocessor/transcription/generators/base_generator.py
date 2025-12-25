from abc import (
    ABC,
    abstractmethod,
)
import json
from pathlib import Path
from typing import (
    Any,
    Dict,
)

from preprocessor.utils.error_handling_logger import ErrorHandlingLogger


class BaseTranscriptionGenerator(ABC):
    def __init__(
        self,
        input_dir: Path,
        output_dir: Path,
        logger: ErrorHandlingLogger,
    ):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.logger = logger

    def generate(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)

        for json_file in self.input_dir.rglob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                self._process_file(json_file, data)

            except Exception as e:  # pylint: disable=broad-exception-caught
                self.logger.error(f"Failed to generate output for {json_file}: {e}")

    @abstractmethod
    def _process_file(self, json_file: Path, data: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def _get_output_filename(self, json_file: Path) -> str:
        pass
