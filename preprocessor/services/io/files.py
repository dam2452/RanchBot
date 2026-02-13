import json
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
)


class FileOperations:
    @staticmethod
    def atomic_write_json(path: Path, data: Dict[str, Any], indent: int = 2) -> None:
        def __write_temp(temp_path: Path) -> None:
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=indent)

        FileOperations.__execute_atomic_write(path, __write_temp)

    @staticmethod
    def load_json(path: Path) -> Dict[str, Any]:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def __execute_atomic_write(path: Path, write_func: Callable[[Path], None]) -> None:
        temp_path = path.with_suffix(f'{path.suffix}.tmp')
        try:
            write_func(temp_path)
            temp_path.replace(path)
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise
