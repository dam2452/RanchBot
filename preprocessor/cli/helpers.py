from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from preprocessor.core.context import ExecutionContext
from preprocessor.core.state_manager import StateManager
from preprocessor.services.core.logging import ErrorHandlingLogger
from preprocessor.services.episodes.episode_manager import EpisodeManager
from preprocessor.services.io.path_service import PathService


@dataclass
class PipelineSetup:
    context: ExecutionContext
    logger: ErrorHandlingLogger
    state_manager: StateManager
    episode_manager: Optional[EpisodeManager] = None


class PipelineContextFactory:

    @staticmethod
    def build(
        series: str,
        logger_name: str,
        force_rerun: bool = False,
        with_episode_manager: bool = True,
    ) -> PipelineSetup:
        logger = PipelineContextFactory.__create_logger(logger_name)
        base_dir = PathService.get_output_base()
        series_output_dir = PipelineContextFactory.__ensure_output_dir(base_dir, series)

        state_manager = PipelineContextFactory.__create_state_manager(series, series_output_dir)

        context = ExecutionContext(
            series_name=series,
            base_output_dir=base_dir,
            logger=logger,
            state_manager=state_manager,
            force_rerun=force_rerun,
        )

        episode_manager = None
        if with_episode_manager:
            input_base = PathService.get_input_base()
            episode_manager = PipelineContextFactory.__create_episode_manager(
                series, input_base, logger,
            )

        return PipelineSetup(
            logger=logger,
            state_manager=state_manager,
            context=context,
            episode_manager=episode_manager,
        )

    @staticmethod
    def __create_episode_manager(
        series: str, input_base: Path, logger: ErrorHandlingLogger,
    ) -> Optional[EpisodeManager]:
        episodes_json: Optional[Path] = input_base / series / 'episodes.json'
        if not episodes_json.exists():
            episodes_json = None
        return EpisodeManager(episodes_json, series, logger)
    @staticmethod
    def __create_logger(
        command_name: str,
        loglevel: int = ErrorHandlingLogger.INFO,
    ) -> ErrorHandlingLogger:
        return ErrorHandlingLogger(class_name=command_name, loglevel=loglevel, error_exit_code=1)

    @staticmethod
    def __create_state_manager(series_name: str, working_dir: Path) -> StateManager:
        state_manager = StateManager(series_name=series_name, working_dir=working_dir)
        state_manager.load_or_create_state()
        return state_manager

    @staticmethod
    def __ensure_output_dir(base_dir: Path, series: str) -> Path:
        series_output_dir = base_dir / series
        series_output_dir.mkdir(parents=True, exist_ok=True)
        return series_output_dir


def setup_pipeline_context(
    series: str,
    logger_name: str,
    force_rerun: bool = False,
    with_episode_manager: bool = True,
) -> PipelineSetup:
    return PipelineContextFactory.build(series, logger_name, force_rerun, with_episode_manager)


def create_cli_logger(command_name: str, loglevel: int = ErrorHandlingLogger.INFO) -> ErrorHandlingLogger:
    return ErrorHandlingLogger(class_name=command_name, loglevel=loglevel, error_exit_code=1)
