from pathlib import Path
from typing import (
    TYPE_CHECKING,
    List,
    Optional,
)

from preprocessor.config.config import Settings
from preprocessor.config.settings_factory import SettingsFactory
from preprocessor.core.model_pool import ModelPool
from preprocessor.services.core.logging import ErrorHandlingLogger

if TYPE_CHECKING:
    from preprocessor.core.state_manager import StateManager
    from preprocessor.services.episodes.episode_manager import EpisodeInfo


class ExecutionContext:
    def __init__(
            self,
            series_name: str,
            base_output_dir: Path,
            logger: ErrorHandlingLogger,
            state_manager: Optional['StateManager'] = None,
            force_rerun: bool = False,
            disable_parallel: bool = False,
            settings_instance: Optional[Settings] = None,
    ) -> None:
        self.__series_name: str = series_name
        self.__base_output_dir: Path = base_output_dir / series_name
        self.__state_manager: Optional['StateManager'] = state_manager
        self.__force_rerun: bool = force_rerun
        self.__disable_parallel: bool = disable_parallel
        self.__logger: ErrorHandlingLogger = logger
        self.__settings: Settings = settings_instance or SettingsFactory.get_settings()
        self.__model_pool: ModelPool = ModelPool()

    @property
    def disable_parallel(self) -> bool:
        return self.__disable_parallel

    @property
    def force_rerun(self) -> bool:
        return self.__force_rerun

    @property
    def logger(self) -> ErrorHandlingLogger:
        return self.__logger

    @property
    def model_pool(self) -> ModelPool:
        return self.__model_pool

    @property
    def series_name(self) -> str:
        return self.__series_name

    @property
    def settings(self) -> Settings:
        """Get active Settings instance for this context."""
        return self.__settings

    @property
    def state_manager(self) -> Optional['StateManager']:
        return self.__state_manager

    def get_output_path(
            self, episode_info: 'EpisodeInfo', subdir: str, filename: str,
    ) -> Path:
        season_code: str = episode_info.season_code()
        episode_code: str = episode_info.episode_num()

        path = self.__base_output_dir / subdir / season_code / episode_code / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def get_season_output_path(
            self, episode_info: 'EpisodeInfo', subdir: str, filename: str,
    ) -> Path:
        season_code: str = episode_info.season_code()

        path = self.__base_output_dir / subdir / season_code / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def is_step_completed(self, step_name: str, episode_id: str) -> bool:
        if not self.__state_manager:
            return False
        return self.__state_manager.is_step_completed(step_name, episode_id)

    def mark_step_completed(self, step_name: str, episode_id: str) -> None:
        if self.__state_manager:
            self.__state_manager.mark_step_completed(step_name, episode_id)

    def mark_step_started(
            self, step_name: str, episode_id: str, temp_files: Optional[List[str]] = None,
    ) -> None:
        if self.__state_manager:
            self.__state_manager.mark_step_started(step_name, episode_id, temp_files)
