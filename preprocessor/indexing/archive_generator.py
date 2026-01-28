import logging
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
)
import zipfile

from preprocessor.config.config import settings
from preprocessor.core.base_processor import (
    BaseProcessor,
    OutputSpec,
    ProcessingItem,
)
from preprocessor.core.constants import (
    FILE_EXTENSIONS,
    FILE_SUFFIXES,
)
from preprocessor.core.episode_manager import EpisodeManager
from preprocessor.utils.console import console

ELASTIC_SUBDIRS = settings.output_subdirs.elastic_document_subdirs


class ArchiveGenerator(BaseProcessor):
    FOLDER_TO_FILE_SUFFIX = {
        ELASTIC_SUBDIRS.text_segments: "text_segments",
        ELASTIC_SUBDIRS.text_embeddings: "text_embeddings",
        ELASTIC_SUBDIRS.video_frames: "video_frames",
        ELASTIC_SUBDIRS.episode_names: "episode_name",
        ELASTIC_SUBDIRS.text_statistics: "text_statistics",
        ELASTIC_SUBDIRS.full_episode_embeddings: "full_episode_embedding",
        ELASTIC_SUBDIRS.sound_events: "sound_events",
        ELASTIC_SUBDIRS.sound_event_embeddings: "sound_event_embeddings",
    }

    def __init__(self, args: Dict[str, Any]):
        super().__init__(
            args=args,
            class_name=self.__class__.__name__,
            error_exit_code=11,
            loglevel=logging.DEBUG,
        )

        self.elastic_documents_dir: Path = self._args["elastic_documents_dir"]
        self.output_dir: Path = self._args.get("output_dir", Path("/app/output_data/archives"))
        self.allow_partial: bool = self._args.get("allow_partial", False)

        episodes_info_json = self._args.get("episodes_info_json")
        self.episode_manager = EpisodeManager(episodes_info_json, self.series_name)

    def _validate_args(self, args: Dict[str, Any]) -> None:
        if "elastic_documents_dir" not in args:
            raise ValueError("elastic_documents_dir is required")

    def _get_processing_items(self) -> List[ProcessingItem]:
        segments_dir = self.elastic_documents_dir / ELASTIC_SUBDIRS.text_segments
        if not segments_dir.exists():
            console.print(f"[yellow]Text segments directory not found: {segments_dir}[/yellow]")
            return []

        all_segment_files = list(segments_dir.glob(f"**/*{FILE_SUFFIXES['text_segments']}{FILE_EXTENSIONS['jsonl']}"))
        items = []

        for segment_file in all_segment_files:
            episode_info = self.episode_manager.parse_filename(segment_file)
            if not episode_info:
                self.logger.warning(f"Cannot parse episode info from {segment_file}")
                continue

            base_name = segment_file.stem.replace(FILE_SUFFIXES["text_segments"], "")
            items.append(
                ProcessingItem(
                    episode_id=episode_info.episode_code(),
                    input_path=segment_file,
                    metadata={
                        "base_name": base_name,
                        "episode_info": episode_info,
                    },
                ),
            )

        return items

    def _get_expected_outputs(self, item: ProcessingItem) -> List[OutputSpec]:
        episode_info = item.metadata["episode_info"]
        base_name = item.metadata["base_name"]

        archive_name = f"{base_name}_elastic_documents.zip"
        archive_path = (
            self.output_dir
            / f"S{episode_info.season:02d}"
            / f"E{episode_info.relative_episode:02d}"
            / archive_name
        )

        return [OutputSpec(path=archive_path, required=True)]

    def _process_item(self, item: ProcessingItem, missing_outputs: List[OutputSpec]) -> None:
        episode_info = item.metadata["episode_info"]
        base_name = item.metadata["base_name"]

        console.print(f"[cyan]Archiving documents for: {item.episode_id}[/cyan]")

        episode_files = self._collect_episode_files(episode_info, base_name)

        if not episode_files:
            self.logger.warning(f"No files found for {item.episode_id}")
            return

        expected_count = len(self.FOLDER_TO_FILE_SUFFIX)
        found_count = len(episode_files)

        if found_count < expected_count and not self.allow_partial:
            console.print(
                f"[yellow]Skipping {item.episode_id}: incomplete files "
                f"({found_count}/{expected_count}). Use --allow-partial to archive anyway.[/yellow]",
            )
            return

        for output_spec in missing_outputs:
            self._create_archive(output_spec.path, episode_files)

        console.print(f"[green]Completed archive for: {item.episode_id}[/green]")

    def _collect_episode_files(self, episode_info, base_name: str) -> Dict[str, Path]:
        collected_files = {}

        for folder_name, file_suffix in self.FOLDER_TO_FILE_SUFFIX.items():
            file_name = f"{base_name}_{file_suffix}.jsonl"
            file_path = (
                self.elastic_documents_dir
                / folder_name
                / f"S{episode_info.season:02d}"
                / f"E{episode_info.relative_episode:02d}"
                / file_name
            )

            if file_path.exists():
                collected_files[folder_name] = file_path
            else:
                self.logger.warning(f"File not found: {file_path}")

        return collected_files

    def _create_archive(self, archive_path: Path, files: Dict[str, Path]) -> None:
        archive_path.parent.mkdir(parents=True, exist_ok=True)

        temp_path = archive_path.with_suffix(archive_path.suffix + ".tmp")

        try:
            with zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for _, file_path in files.items():
                    zipf.write(file_path, arcname=file_path.name)
                    self.logger.debug(f"Added to archive: {file_path.name}")

            temp_path.replace(archive_path)

            archive_size_mb = archive_path.stat().st_size / (1024 * 1024)
            console.print(
                f"[green]Created archive: {archive_path.name} "
                f"({len(files)} files, {archive_size_mb:.2f} MB)[/green]",
            )

        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            raise RuntimeError(f"Failed to create archive {archive_path}: {e}") from e
