from pathlib import Path
from typing import (
    TYPE_CHECKING,
    List,
    Optional,
)

from preprocessor.lib.core.logging import ErrorHandlingLogger

if TYPE_CHECKING:
    from preprocessor.core.state_manager import StateManager
    from preprocessor.lib.episodes.episode_manager import EpisodeInfo

class ExecutionContext:

    def __init__(
        self,
        series_name: str,
        base_output_dir: Path,
        logger: ErrorHandlingLogger,
        state_manager: Optional['StateManager'] = None,
        force_rerun: bool = False,
    ) -> None:
        self._series_name: str = series_name
        self._base_output_dir: Path = base_output_dir / series_name
        self._state_manager: Optional['StateManager'] = state_manager
        self._force_rerun: bool = force_rerun
        self._logger: ErrorHandlingLogger = logger

    @property
    def force_rerun(self) -> bool:
        return self._force_rerun

    def get_output_path(
        self, episode_info: 'EpisodeInfo', subdir: str, filename: str,
    ) -> Path:
        season_code: str = episode_info.season_code()
        episode_code: str = episode_info.episode_num()
        path: Path = (
            self._base_output_dir / subdir / season_code / episode_code / filename
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def get_season_output_path(
        self, episode_info: 'EpisodeInfo', subdir: str, filename: str,
    ) -> Path:
        season_code: str = episode_info.season_code()
        path: Path = self._base_output_dir / subdir / season_code / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def is_step_completed(self, step_name: str, episode_id: str) -> bool:
        if not self._state_manager:
            return False
        return self._state_manager.is_step_completed(step_name, episode_id)

    @property
    def logger(self) -> ErrorHandlingLogger:
        return self._logger

    def mark_step_completed(self, step_name: str, episode_id: str) -> None:
        if self._state_manager:
            self._state_manager.mark_step_completed(step_name, episode_id)

    def mark_step_started(
        self, step_name: str, episode_id: str, temp_files: Optional[List[str]] = None,
    ) -> None:
        if self._state_manager:
            self._state_manager.mark_step_started(step_name, episode_id, temp_files)

    @property
    def series_name(self) -> str:
        return self._series_name

    @property
    def state_manager(self) -> Optional['StateManager']:
        return self._state_manager
