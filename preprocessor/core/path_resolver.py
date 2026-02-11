from pathlib import Path

from preprocessor.core.path_service import PathService


class PathResolver:

    @staticmethod
    def get_input_base() -> Path:
        return PathService.get_input_base()

    @staticmethod
    def get_output_base() -> Path:
        return PathService.get_output_base()
    @staticmethod
    def _is_docker() -> bool:
        return PathService._is_docker()
