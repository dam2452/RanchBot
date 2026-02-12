from abc import (
    ABC,
    abstractmethod,
)
from pathlib import Path
from typing import TYPE_CHECKING

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
