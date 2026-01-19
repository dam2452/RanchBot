from dataclasses import dataclass
import json
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
)

from preprocessor.cli_utils.resource_scope import ResourceScope
from preprocessor.config.config import (
    get_output_path,
    settings,
)
from preprocessor.core.processing_metadata import ProcessingMetadata
from preprocessor.core.state_manager import StateManager
from preprocessor.utils.console import console

ELASTIC_SUBDIRS = settings.output_subdirs.elastic_document_subdirs


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

        try:
            exit_code = self._run_all_steps(params)
            if self.state_manager:
                self.state_manager.cleanup()
            self._finalize_metadata(exit_code)
            return exit_code
        except KeyboardInterrupt:
            console.print("\n[yellow]Pipeline interrupted by user[/yellow]")
            self._finalize_metadata(130)
            return 130

    def _run_all_steps(self, params: Dict[str, Any]) -> int:
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

            try:
                with ResourceScope():
                    exit_code = step.execute_func(**params)
            except KeyboardInterrupt:
                console.print(f"\n[yellow]Step {step.step_num} interrupted[/yellow]")
                if step_metadata:
                    step_metadata.finish(130)
                return 130

            if step_metadata:
                step_metadata.finish(exit_code)

            if exit_code != 0:
                console.print(f"[red]Step {step.step_num} failed with exit code {exit_code}[/red]")
                return exit_code

        return 0

    def _finalize_metadata(self, exit_code: int):
        if self.metadata:
            additional_stats = self.__collect_additional_statistics()
            self.metadata.finish_processing(exit_code, additional_stats)

            if self.metadata_output_dir:
                metadata_file = self.metadata_output_dir / f"{self.series_name}_processing_metadata.json"
                self.metadata.save_to_file(metadata_file)
                console.print(f"[green]Processing metadata saved to: {metadata_file}[/green]")

    def __collect_additional_statistics(self) -> Dict[str, Any]:  # pylint: disable=too-many-locals
        stats: Dict[str, Any] = {}
        # noinspection PyBroadException
        try:  # pylint: disable=too-many-try-statements
            transcription_jsons_dir = Path(self.metadata.params.get("transcription_jsons", ""))
            if transcription_jsons_dir.exists():
                transcription_files = list(transcription_jsons_dir.rglob("*_segmented.json"))
                stats["transcription_files_count"] = len(transcription_files)
                stats["transcription_files"] = [f.name for f in transcription_files[:20]]

            transcoded_videos_dir = Path(self.metadata.params.get("transcoded_videos", ""))
            if transcoded_videos_dir.exists():
                video_files = list(transcoded_videos_dir.rglob("*.mp4"))
                stats["transcoded_videos_count"] = len(video_files)
                total_size = sum(f.stat().st_size for f in video_files if f.is_file())
                stats["transcoded_videos_total_size_mb"] = round(total_size / (1024 * 1024), 2)

            output_frames_dir = Path(settings.frame_export.output_dir)
            if output_frames_dir.exists():
                frame_metadata_files = list(output_frames_dir.rglob("frame_metadata.json"))
                stats["processed_episodes_count"] = len(frame_metadata_files)
                total_frames = 0
                for metadata_file in frame_metadata_files:
                    try:
                        with open(metadata_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            total_frames += data.get("statistics", {}).get("total_frames", 0)
                    except Exception:  # pylint: disable=broad-exception-caught
                        pass
                stats["total_frames_extracted"] = total_frames

            embeddings_dir = Path(settings.embedding.default_output_dir)
            if embeddings_dir.exists():
                text_embedding_files = list(embeddings_dir.rglob("embeddings_text.json"))
                video_embedding_files = list(embeddings_dir.rglob("embeddings_video.json"))
                stats["text_embedding_files_count"] = len(text_embedding_files)
                stats["video_embedding_files_count"] = len(video_embedding_files)

            image_hashes_dir = Path(settings.image_hash.output_dir)
            if image_hashes_dir.exists():
                hash_files = list(image_hashes_dir.rglob("image_hashes.json"))
                stats["image_hash_files_count"] = len(hash_files)

            elastic_docs_dir = get_output_path("elastic_documents")
            if elastic_docs_dir.exists():
                segment_files = list((elastic_docs_dir / ELASTIC_SUBDIRS.segments).rglob("*.jsonl"))
                text_emb_files = list((elastic_docs_dir / ELASTIC_SUBDIRS.text_embeddings).rglob("*.jsonl"))
                video_frame_files = list((elastic_docs_dir / ELASTIC_SUBDIRS.video_frames).rglob("*.jsonl"))
                stats["elastic_documents"] = {
                    ELASTIC_SUBDIRS.segments: len(segment_files),
                    ELASTIC_SUBDIRS.text_embeddings: len(text_emb_files),
                    ELASTIC_SUBDIRS.video_frames: len(video_frame_files),
                }

        except Exception: # pylint: disable=broad-exception-caught
            pass

        return stats
