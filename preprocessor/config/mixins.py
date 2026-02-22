from pathlib import Path
from typing import ClassVar

from preprocessor.config.output_paths import get_base_output_dir


class OutputDirMixin:
    OUTPUT_SUBDIR: ClassVar[str]

    @classmethod
    def get_output_dir(cls, series_name: str) -> Path:
        if not hasattr(cls, 'OUTPUT_SUBDIR'):
            raise NotImplementedError(
                f"{cls.__name__} must define OUTPUT_SUBDIR class variable",
            )
        return get_base_output_dir(series_name) / cls.OUTPUT_SUBDIR
