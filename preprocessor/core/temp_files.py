from pathlib import Path
from typing import Optional


class StepTempFile:
    def __init__(self, final_path: Path, temp_suffix: str = '.tmp') -> None:
        self.__final_path: Path = final_path
        self.__temp_suffix: str = temp_suffix
        self.__temp_path: Optional[Path] = None

    @property
    def final_path(self) -> Path:
        return self.__final_path

    @property
    def temp_path(self) -> Path:
        if self.__temp_path is None:
            raise RuntimeError('Context manager not entered yet')
        return self.__temp_path

    def __enter__(self) -> Path:
        self.__temp_path = self.__final_path.with_suffix(
            f'{self.__final_path.suffix}{self.__temp_suffix}',
        )
        self.__temp_path.parent.mkdir(parents=True, exist_ok=True)
        return self.__temp_path

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if self.__temp_path is None:
            return False

        if exc_type is None:
            self.__temp_path.replace(self.__final_path)
        elif self.__temp_path.exists():
            self.__temp_path.unlink()

        return False
