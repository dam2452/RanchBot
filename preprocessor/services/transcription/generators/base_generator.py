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

from preprocessor.services.core.logging import ErrorHandlingLogger


class BaseTranscriptionGenerator(ABC):
    def __init__(self, input_dir: Path, output_dir: Path, logger: ErrorHandlingLogger) -> None:
        self._input_dir = input_dir
        self._output_dir = output_dir
        self._logger = logger

    def generate(self) -> None:
        self._output_dir.mkdir(parents=True, exist_ok=True)
        for json_file in self._input_dir.rglob('*.json'):
            try:
                data = self.__load_json(json_file)
                if data:
                    self._process_file(json_file, data)
            except Exception as e:
                self._logger.error(f'Failed to generate output for {json_file}: {e}')

    @staticmethod
    def __load_json(file_path: Path) -> Dict[str, Any]:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    @abstractmethod
    def _get_output_filename(self, json_file: Path) -> str:
        ...

    @abstractmethod
    def _process_file(self, json_file: Path, data: Dict[str, Any]) -> None:
        ...
