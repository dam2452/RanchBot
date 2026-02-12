from abc import (
    ABC,
    abstractmethod,
)
import json
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Optional,
)

from preprocessor.services.validation.file_validators import FileValidator

if TYPE_CHECKING:
    from preprocessor.services.validation.episode_stats import EpisodeStats


class BaseValidator(ABC):

    @abstractmethod
    def validate(self, stats: 'EpisodeStats') -> None:
        pass

    @staticmethod
    def _check_path_exists(
        path: Path, stats: 'EpisodeStats', error_msg: str,
    ) -> bool:
        if not path.exists():
            stats.errors.append(error_msg)
            return False
        return True

    @staticmethod
    def _add_warning(stats: 'EpisodeStats', message: str) -> None:
        stats.warnings.append(message)

    @staticmethod
    def _add_error(stats: 'EpisodeStats', message: str) -> None:
        stats.errors.append(message)

    @staticmethod
    def _validate_json_if_exists(
        stats: 'EpisodeStats',
        file_path: Path,
        error_msg_prefix: str,
    ) -> bool:
        if not file_path.exists():
            return False

        result = FileValidator.validate_json_file(file_path)
        if not result.is_valid:
            BaseValidator._add_error(stats, f'{error_msg_prefix}: {result.error_message}')
            return False
        return True

    @staticmethod
    def _validate_json_with_warning(
        stats: 'EpisodeStats',
        file_path: Path,
        missing_msg: str,
        invalid_msg_prefix: str,
    ) -> bool:
        if not file_path.exists():
            BaseValidator._add_warning(stats, missing_msg)
            return False

        result = FileValidator.validate_json_file(file_path)
        if not result.is_valid:
            BaseValidator._add_warning(stats, f'{invalid_msg_prefix}: {result.error_message}')
            return False
        return True

    @staticmethod
    def _validate_json_with_error(
        stats: 'EpisodeStats',
        file_path: Path,
        missing_msg: str,
        invalid_msg_prefix: str,
    ) -> bool:
        if not file_path.exists():
            BaseValidator._add_error(stats, missing_msg)
            return False

        result = FileValidator.validate_json_file(file_path)
        if not result.is_valid:
            BaseValidator._add_error(stats, f'{invalid_msg_prefix}: {result.error_message}')
            return False
        return True

    @staticmethod
    def _load_json_safely(file_path: Path) -> Optional[Dict[str, Any]]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None
