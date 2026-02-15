import json
from pathlib import Path
from typing import (
    Any,
    Dict,
)

from preprocessor.core.temp_files import StepTempFile


class FileOperations:
    @staticmethod
    def atomic_write_json(path: Path, data: Dict[str, Any], indent: int = 2) -> None:
        with StepTempFile(path) as temp_path:
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=indent)

    @staticmethod
    def load_json(path: Path) -> Dict[str, Any]:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
