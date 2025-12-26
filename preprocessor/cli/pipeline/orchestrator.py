from dataclasses import dataclass
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
)

from preprocessor.cli_utils.resource_scope import ResourceScope
from preprocessor.config.config import settings
from preprocessor.core.processing_metadata import ProcessingMetadata
from preprocessor.core.state_manager import StateManager
from preprocessor.utils.console import console


@dataclass
class PipelineStep:
    name: str
    step_num: str
    execute_func: Callable
    skip: bool = False


class PipelineOrchestrator:
    def __init__(self, state_manager: Optional[StateManager] = None, series_name: Optional[str] = None, metadata_output_dir: Optional[Path] = None):
        self.state_manager = state_manager
        self.steps: List[PipelineStep] = []
        self.series_name = series_name
        self.metadata_output_dir = metadata_output_dir
        self.metadata: Optional[ProcessingMetadata] = None

    def add_step(self, name: str, step_num: str, func: Callable, skip: bool = False):
        self.steps.append(PipelineStep(name, step_num, func, skip))

    def execute(self, **params) -> int:
        if self.series_name:
            self.metadata = ProcessingMetadata(series_name=self.series_name, params=params)

        for step in self.steps:
            step_metadata = None
            if self.metadata:
                step_metadata = self.metadata.add_step(name=step.name, step_num=step.step_num)

            if step.skip:
                console.print(f"[yellow]Step {step.step_num}: {step.name} - SKIPPED[/yellow]")
                if step_metadata:
                    step_metadata.skip()
                continue

            console.print(f"[bold blue]Step {step.step_num}: {step.name}[/bold blue]")

            if step_metadata:
                step_metadata.start()

            with ResourceScope():
                exit_code = step.execute_func(**params)

            if step_metadata:
                step_metadata.finish(exit_code)

            if exit_code != 0:
                console.print(f"[red]Step {step.step_num} failed with exit code {exit_code}[/red]")
                self._finalize_metadata(exit_code)
                return exit_code

        if self.state_manager:
            self.state_manager.cleanup()

        self._finalize_metadata(0)
        return 0

    def _finalize_metadata(self, exit_code: int):
        if self.metadata:
            additional_stats = self.__collect_additional_statistics()
            self.metadata.finish_processing(exit_code, additional_stats)

            if self.metadata_output_dir:
                metadata_file = self.metadata_output_dir / f"{self.series_name}_processing_metadata.json"
                self.metadata.save_to_file(metadata_file)
                console.print(f"[green]Processing metadata saved to: {metadata_file}[/green]")

    def __collect_additional_statistics(self) -> Dict[str, Any]:
        stats: Dict[str, Any] = {}
        # noinspection PyBroadException
        try:
            transcription_jsons_dir = Path(self.metadata.params.get("transcription_jsons", ""))
            if transcription_jsons_dir.exists():
                transcription_files = list(transcription_jsons_dir.glob("*.json"))
                stats["transcription_files_count"] = len(transcription_files)
                stats["transcription_files"] = [f.name for f in transcription_files]

            transcoded_videos_dir = Path(self.metadata.params.get("transcoded_videos", ""))
            if transcoded_videos_dir.exists():
                video_files = list(transcoded_videos_dir.glob("*"))
                stats["transcoded_videos_count"] = len(video_files)

            embeddings_dir = Path(settings.embedding.default_output_dir)
            if embeddings_dir.exists():
                embedding_files = list(embeddings_dir.glob("*.npy"))
                stats["embedding_files_count"] = len(embedding_files)

        except Exception: # pylint: disable=broad-exception-caught
            pass

        return stats
