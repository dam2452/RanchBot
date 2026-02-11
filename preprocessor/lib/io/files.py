import json
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
)


class FileOperations:

    @staticmethod
    def __atomic_write(path: Path, write_func: Callable[[Any], None]) -> None:
        temp_path = path.with_suffix(path.suffix + '.tmp')
        try:
            write_func(temp_path)
            temp_path.replace(path)
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise

    @staticmethod
    def atomic_write_json(path: Path, data: Dict[str, Any], indent: int=2) -> None:

        def __write(temp: Path) -> None:
            with open(temp, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=indent)
        FileOperations.__atomic_write(path, __write)

    @staticmethod
    def load_json(path: Path) -> Dict[str, Any]:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def __atomic_write_text(path: Path, content: str) -> None: # pylint: disable=unused-private-member

        def __write(temp: Path) -> None:
            with open(temp, 'w', encoding='utf-8') as f:
                f.write(content)
        FileOperations.__atomic_write(path, __write)

def atomic_write_json(path: Path, data: Dict[str, Any], indent: int=2) -> None:
    FileOperations.atomic_write_json(path, data, indent)

def load_json(path: Path) -> Dict[str, Any]:
    return FileOperations.load_json(path)
