from abc import (
    ABC,
    abstractmethod,
)
from dataclasses import dataclass
import logging
from pathlib import Path
import re
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

from preprocessor.core.constants import (
    FILE_SUFFIXES,
    SUPPORTED_VIDEO_EXTENSIONS,
)
from preprocessor.core.state_manager import StateManager
from preprocessor.utils.console import (
    console,
    create_progress,
)
from preprocessor.utils.error_handling_logger import ErrorHandlingLogger


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
    SUPPORTED_VIDEO_EXTENSIONS = SUPPORTED_VIDEO_EXTENSIONS

    def __init__(
        self,
        args: Dict[str, Any],
        class_name: str,
        error_exit_code: int,
        loglevel: int = logging.DEBUG,
    ):
        self._validate_args(args)
        self._args = args

        self.logger = ErrorHandlingLogger(
            class_name=class_name,
            loglevel=loglevel,
            error_exit_code=error_exit_code,
        )

        self.state_manager: Optional[StateManager] = args.get("state_manager")
        self.series_name: str = args.get("series_name", "unknown")

        from preprocessor.utils.progress_tracker import ProgressTracker  # pylint: disable=import-outside-toplevel
        self.progress = args.get("progress_tracker", ProgressTracker())

    @classmethod
    def get_video_glob_patterns(cls) -> List[str]:
        return [f"*{ext}" for ext in cls.SUPPORTED_VIDEO_EXTENSIONS]

    @abstractmethod
    def _validate_args(self, args: Dict[str, Any]) -> None:
        pass

    def work(self) -> int:
        try:
            self._execute()
        except KeyboardInterrupt:
            console.print("\n[yellow]Process interrupted by user[/yellow]")
            self.cleanup()
            self.logger.finalize()
            return 130
        except Exception as e:
            self.logger.error(f"{self.__class__.__name__} failed: {e}")

        self.cleanup()
        return self.logger.finalize()

    def cleanup(self) -> None:
        pass

    def _load_resources(self) -> bool:
        return True

    def _get_processing_info(self) -> List[str]:
        return []

    @staticmethod
    def _get_episode_processing_items_from_metadata(
        metadata_pattern: str,
        base_dir: Path,
        episode_manager: "EpisodeManager",
    ) -> List[ProcessingItem]:
        all_metadata_files = list(base_dir.glob(metadata_pattern))
        items = []

        for metadata_file in all_metadata_files:
            episode_info = episode_manager.parse_filename(metadata_file)
            if not episode_info:
                continue

            episode_id = episode_manager.get_episode_id_for_state(episode_info)

            items.append(
                ProcessingItem(
                    episode_id=episode_id,
                    input_path=metadata_file,
                    metadata={
                        "episode_info": episode_info,
                        "series_name": episode_manager.series_name,
                    },
                ),
            )

        return items

    def _get_processing_items(self) -> List[ProcessingItem]:
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement _get_processing_items() "
            "or override _execute() directly (legacy mode)",
        )

    def _get_expected_outputs(self, item: ProcessingItem) -> List[OutputSpec]:
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement _get_expected_outputs() "
            "or override _execute() directly (legacy mode)",
        )

    def _process_item(self, item: ProcessingItem, missing_outputs: List[OutputSpec]) -> None:
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement _process_item() "
            "or override _execute() directly (legacy mode)",
        )

    def _get_step_name(self) -> str:
        class_name = self.__class__.__name__
        name = class_name.replace("Processor", "").replace("Generator", "").replace("Detector", "")
        name = name.replace("Transcoder", "").replace("Importer", "").replace("Indexer", "")
        return self._to_snake_case(name)

    @staticmethod
    def _to_snake_case(name: str) -> str:
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()

    def _should_skip_item(self, item: ProcessingItem) -> Tuple[bool, List[OutputSpec], str]:
        expected_outputs = self._get_expected_outputs(item)

        if not expected_outputs:
            return False, [], ""

        missing_outputs = [
            output for output in expected_outputs
            if not output.path.exists() or output.path.stat().st_size == 0
        ]

        step_name = self._get_step_name()
        state_completed = (
            self.state_manager and
            self.state_manager.is_step_completed(step_name, item.episode_id)
        )

        if not missing_outputs and state_completed:
            return True, [], f"[yellow]Skipping (completed): {item.episode_id}[/yellow]"

        if not missing_outputs and not state_completed:
            if self.state_manager:
                self.state_manager.mark_step_completed(step_name, item.episode_id)
            return True, [], f"[yellow]Skipping (files exist, state synced): {item.episode_id}[/yellow]"

        if missing_outputs and state_completed:
            console.print(
                f"[yellow]Warning: State marked complete but outputs missing for {item.episode_id}[/yellow]",
            )
            return False, missing_outputs, ""

        return False, missing_outputs, ""

    def _execute(self) -> None:
        all_items = self._get_processing_items()

        if not all_items:
            console.print("[yellow]No items to process[/yellow]")
            return

        items_to_process = []
        skipped_count = 0
        skip_messages = []

        for item in all_items:
            should_skip, missing_outputs, skip_message = self._should_skip_item(item)

            if should_skip:
                if skip_message:
                    skip_messages.append(skip_message)
                skipped_count += 1
            else:
                item.metadata['missing_outputs'] = missing_outputs
                items_to_process.append(item)

        if not items_to_process:
            console.print(
                f"[yellow]All items already processed ({len(all_items)} total, {skipped_count} skipped)[/yellow]",
            )
            return

        for skip_message in skip_messages:
            console.print(skip_message)

        console.print(
            f"[blue]Processing {len(items_to_process)} items "
            f"(of {len(all_items)} total, {skipped_count} skipped)[/blue]",
        )

        self._execute_processing(items_to_process)

    def _execute_processing(self, items: List[ProcessingItem]) -> None:
        if not items:
            console.print("[yellow]No items to process, skipping resource loading[/yellow]")
            return

        for info_line in self._get_processing_info():
            console.print(info_line)

        if not self._load_resources():
            return

        step_name = self._get_step_name()

        try:
            with create_progress() as progress:
                task = progress.add_task(
                    self._get_progress_description(),
                    total=len(items),
                )

                for item in items:
                    try:
                        if self.state_manager:
                            temp_files = self._get_temp_files(item)
                            self.state_manager.mark_step_started(
                                step_name,
                                item.episode_id,
                                temp_files,
                            )

                        missing_outputs = item.metadata.get('missing_outputs', [])
                        self._process_item(item, missing_outputs)

                        if self.state_manager:
                            self.state_manager.mark_step_completed(step_name, item.episode_id)

                    except Exception as e:
                        self.logger.error(f"Failed to process {item.episode_id}: {e}")
                    finally:
                        progress.advance(task)
        except KeyboardInterrupt:
            console.print("\n[yellow]Processing interrupted[/yellow]")
            raise

    def _get_temp_files(self, item: ProcessingItem) -> List[str]:  # pylint: disable=unused-argument
        return []

    def _get_progress_description(self) -> str:
        return f"Processing {self.__class__.__name__}"

    def _create_video_processing_items(
        self,
        source_path: Path,
        extensions: List[str],
        episode_manager: "EpisodeManager",
        skip_unparseable: bool = True,
        subdirectory_filter: Optional[str] = None,
    ) -> List[ProcessingItem]:
        from preprocessor.core.episode_manager import EpisodeManager  # pylint: disable=import-outside-toplevel

        video_files = []

        if source_path.is_file():
            video_files = [source_path]
        else:
            for ext in extensions:
                if subdirectory_filter:
                    pattern = f"**/{subdirectory_filter}/{ext}"
                else:
                    pattern = f"**/{ext}"
                video_files.extend(source_path.glob(pattern))

        items = []
        for video_file in sorted(video_files):
            episode_info = episode_manager.parse_filename(video_file)

            if not episode_info:
                if skip_unparseable:
                    self.logger.error(f"Cannot parse episode info from {video_file.name}")
                    continue
                episode_id = video_file.stem
            else:
                episode_id = EpisodeManager.get_episode_id_for_state(episode_info)

            items.append(
                ProcessingItem(
                    episode_id=episode_id,
                    input_path=video_file,
                    metadata={
                        "episode_info": episode_info,
                    },
                ),
            )

        return items

    def _create_transcription_processing_item(self, transcription_file: Path) -> ProcessingItem:
        from preprocessor.core.episode_manager import EpisodeManager  # pylint: disable=import-outside-toplevel

        base_name = transcription_file.stem.replace(FILE_SUFFIXES["segmented"], "").replace(FILE_SUFFIXES["simple"], "")

        episode_info = self.episode_manager.parse_filename(transcription_file) if hasattr(self, 'episode_manager') else None
        if episode_info:
            episode_id = EpisodeManager.get_episode_id_for_state(episode_info)
        else:
            episode_id = base_name

        return ProcessingItem(
            episode_id=episode_id,
            input_path=transcription_file,
            metadata={
                "base_name": base_name,
            },
        )
