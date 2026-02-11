from dataclasses import dataclass
import logging
import os
from pathlib import Path
from typing import Optional

from preprocessor.core.context import ExecutionContext
from preprocessor.core.state_manager import StateManager
from preprocessor.lib.core.logging import ErrorHandlingLogger
from preprocessor.lib.episodes.episode_manager import EpisodeManager
from preprocessor.lib.ui.console import console


def create_cli_logger(command_name: str, loglevel: int=logging.INFO) -> ErrorHandlingLogger:
    return ErrorHandlingLogger(class_name=command_name, loglevel=loglevel, error_exit_code=1)

def create_state_manager(name: str, no_state: bool) -> Optional[StateManager]:
    if no_state or not name:
        return None
    state_manager: StateManager = StateManager(series_name=name, working_dir=Path('.'))
    state_manager.register_interrupt_handler()
    state_manager.load_or_create_state()
    resume_info: Optional[str] = state_manager.get_resume_info()
    if resume_info:
        console.print(f'[cyan]{resume_info}[/cyan]')
    return state_manager

def create_execution_context(
    name: str,
    logger: ErrorHandlingLogger,
    no_state: bool = False,
    force_rerun: bool = False,
) -> ExecutionContext:
    state_manager: Optional[StateManager] = create_state_manager(name, no_state)
    return ExecutionContext(
        series_name=name,
        base_output_dir=Path('preprocessor/output_data'),
        state_manager=state_manager,
        force_rerun=force_rerun,
        logger=logger,
    )

@dataclass
class PipelineSetup:
    logger: ErrorHandlingLogger
    state_manager: StateManager
    context: ExecutionContext
    episode_manager: Optional[EpisodeManager] = None

def setup_pipeline_context(
    series: str,
    logger_name: str,
    force_rerun: bool = False,
    with_episode_manager: bool = True,
) -> PipelineSetup:
    logger: ErrorHandlingLogger = create_cli_logger(logger_name)

    is_docker: bool = os.getenv('DOCKER_CONTAINER', 'false').lower() == 'true'
    base_dir: Path = Path('/app/output_data') if is_docker else Path('preprocessor/output_data')

    series_output_dir: Path = base_dir / series
    series_output_dir.mkdir(parents=True, exist_ok=True)

    state_manager: StateManager = StateManager(series, working_dir=series_output_dir)
    state_manager.load_or_create_state()

    context: ExecutionContext = ExecutionContext(
        series_name=series,
        base_output_dir=base_dir,
        logger=logger,
        state_manager=state_manager,
        force_rerun=force_rerun,
    )
    episode_manager: Optional[EpisodeManager] = None
    if with_episode_manager:
        input_base: Path = Path('/input_data') if is_docker else Path('preprocessor/input_data')
        episodes_json: Optional[Path] = input_base / series / 'episodes.json'
        if not episodes_json.exists():
            episodes_json = None
        episode_manager = EpisodeManager(episodes_json, series, logger)
    return PipelineSetup(
        logger=logger,
        state_manager=state_manager,
        context=context,
        episode_manager=episode_manager,
    )
