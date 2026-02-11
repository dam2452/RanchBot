from abc import (
    ABC,
    abstractmethod,
)
from dataclasses import dataclass
from pathlib import Path
import re
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

from preprocessor.config.constants import SUPPORTED_VIDEO_EXTENSIONS
from preprocessor.core.state_manager import StateManager
from preprocessor.services.core.logging import ErrorHandlingLogger
from preprocessor.services.io.path_manager import PathManager
from preprocessor.services.ui.console import (
    SimpleProgress,
    console,
)
from preprocessor.services.ui.progress import ProgressTracker


@dataclass
class ProcessingItem:
    episode_id: str
    input_path: Path
    metadata: Dict[str, Any]

@dataclass
class OutputSpec:
    path: Path
    required: bool = True

class BaseProcessor(ABC):
    DESCRIPTION: str = ''
    PRIORITY: int = 100
    PRODUCES: List[str] = []
    REQUIRES: List[str] = []
    SUPPORTED_VIDEO_EXTENSIONS = SUPPORTED_VIDEO_EXTENSIONS

    def __init__(self, args: Dict[str, Any], class_name: str, error_exit_code: int, loglevel: int = 10) -> None:
        self._validate_args(args)
        self._args = args
        self.logger = ErrorHandlingLogger(class_name=class_name, loglevel=loglevel, error_exit_code=error_exit_code)
        self.state_manager: Optional[StateManager] = args.get('state_manager')
        self.series_name: str = args.get('series_name', 'unknown')
        self.path_manager: PathManager = args.get('path_manager', PathManager(self.series_name))
        self.progress = args.get('progress_tracker', ProgressTracker())

    def cleanup(self) -> None:
        pass

    def _finalize(self) -> None:
        pass

    @abstractmethod
    def get_output_subdir(self) -> str:
        pass

    def work(self) -> int:
        try:
            self._execute()
        except KeyboardInterrupt:
            console.print('\n[yellow]Process interrupted by user[/yellow]')
            self.cleanup()
            self.logger.finalize()
            return 130
        except Exception as e:
            self.logger.error(f'{self.__class__.__name__} failed: {e}')
        self.cleanup()
        return self.logger.finalize()

    def _execute(self) -> None:
        all_items = self._get_processing_items()
        if not all_items:
            console.print('[yellow]No items to process[/yellow]')
            return
        items_to_process = []
        skipped_count = 0
        skip_messages = []
        for item in all_items:
            should_skip, missing_outputs, skip_message = self.__should_skip_item(item)
            if should_skip:
                if skip_message:
                    skip_messages.append(skip_message)
                skipped_count += 1
            else:
                item.metadata['missing_outputs'] = missing_outputs
                items_to_process.append(item)
        if not items_to_process:
            console.print(
                f'[yellow]All items already processed '
                f'({len(all_items)} total, {skipped_count} skipped)[/yellow]',
            )
            return
        for skip_message in skip_messages:
            console.print(skip_message)
        console.print(
            f'[blue]Processing {len(items_to_process)} items '
            f'(of {len(all_items)} total, {skipped_count} skipped)[/blue]',
        )
        self.__execute_processing(items_to_process)
        self._finalize()

    @abstractmethod
    def _get_expected_outputs(self, item: ProcessingItem) -> List[OutputSpec]:
        pass

    @abstractmethod
    def _get_processing_items(self) -> List[ProcessingItem]:
        pass

    def _get_progress_description(self) -> str:
        return f'Processing {self.__class__.__name__}'

    def _load_resources(self) -> bool:
        return True

    @abstractmethod
    def _process_item(
        self, item: ProcessingItem, missing_outputs: List[OutputSpec],
    ) -> None:
        pass

    @abstractmethod
    def _validate_args(self, args: Dict[str, Any]) -> None:
        pass

    def __execute_processing(self, items: List[ProcessingItem]) -> None:
        if not items:
            console.print('[yellow]No items to process, skipping resource loading[/yellow]')
            return
        if not self._load_resources():
            return
        step_name = self.__get_step_name()
        try:
            with SimpleProgress() as progress:
                task = progress.add_task(self._get_progress_description(), total=len(items))
                for item in items:
                    try:
                        if self.state_manager:
                            self.state_manager.mark_step_started(step_name, item.episode_id, [])
                        missing_outputs = item.metadata.get('missing_outputs', [])
                        self._process_item(item, missing_outputs)
                        if self.state_manager:
                            self.state_manager.mark_step_completed(step_name, item.episode_id)
                    except Exception as e:
                        self.logger.error(f'Failed to process {item.episode_id}: {e}')
                    finally:
                        progress.advance(task)
        except KeyboardInterrupt:
            console.print('\n[yellow]Processing interrupted[/yellow]')
            raise

    def __get_step_name(self) -> str:
        class_name = self.__class__.__name__
        suffixes_to_remove = ['Processor', 'Generator', 'Detector', 'Transcoder', 'Importer', 'Indexer']
        name = class_name
        for suffix in suffixes_to_remove:
            name = name.replace(suffix, '')
        return self.__to_snake_case(name)

    def __should_skip_item(
        self, item: ProcessingItem,
    ) -> Tuple[bool, List[OutputSpec], str]:
        expected_outputs = self._get_expected_outputs(item)
        if not expected_outputs:
            return False, [], ''
        missing_outputs = self.__get_missing_outputs(expected_outputs)
        step_name = self.__get_step_name()
        state_completed = self.__is_step_completed_in_state(step_name, item.episode_id)
        has_all_outputs = len(missing_outputs) == 0
        if has_all_outputs and state_completed:
            return True, [], f'[yellow]Skipping (completed): {item.episode_id}[/yellow]'
        if has_all_outputs and not state_completed:
            self.__sync_state_completed(step_name, item.episode_id)
            return True, [], f'[yellow]Skipping (files exist, state synced): {item.episode_id}[/yellow]'
        if not has_all_outputs and state_completed:
            console.print(
                f'[yellow]Warning: State marked complete but outputs missing '
                f'for {item.episode_id}[/yellow]',
            )
        return False, missing_outputs, ''

    @staticmethod
    def __get_missing_outputs(expected_outputs: List[OutputSpec]) -> List[OutputSpec]:
        return [
            output for output in expected_outputs
            if not output.path.exists() or output.path.stat().st_size == 0
        ]

    def __is_step_completed_in_state(self, step_name: str, episode_id: str) -> bool:
        return bool(
            self.state_manager
            and self.state_manager.is_step_completed(step_name, episode_id),
        )

    def __sync_state_completed(self, step_name: str, episode_id: str) -> None:
        if self.state_manager:
            self.state_manager.mark_step_completed(step_name, episode_id)

    @staticmethod
    def __to_snake_case(name: str) -> str:
        name = re.sub('(.)([A-Z][a-z]+)', '\\1_\\2', name)
        return re.sub('([a-z0-9])([A-Z])', '\\1_\\2', name).lower()
