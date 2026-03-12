from pathlib import Path
from typing import (
    Dict,
    List,
)
import zipfile

from preprocessor.config.constants import ELASTIC_DOC_TYPES
from preprocessor.config.step_configs import ArchiveConfig
from preprocessor.core.artifacts import (
    ArchiveArtifact,
    ProcessedEpisode,
)
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.core.output_descriptors import FileOutput
from preprocessor.services.episodes.types import EpisodeInfo


class ArchiveGenerationStep(
    PipelineStep[ProcessedEpisode, ArchiveArtifact, ArchiveConfig],
):
    @property
    def supports_batch_processing(self) -> bool:
        return True

    def execute_batch(
        self, input_data: List[ProcessedEpisode], context: ExecutionContext,
    ) -> List[ArchiveArtifact]:
        return self._execute_with_threadpool(
            input_data, context, self.config.max_parallel_episodes, self.execute,
        )

    def _process(
        self, input_data: ProcessedEpisode, context: ExecutionContext,
    ) -> ArchiveArtifact:
        episode_info = input_data.episode_info
        output_path = self._get_cache_path(input_data, context)

        episode_files = self.__collect_episode_files(context, episode_info)

        expected = len(ELASTIC_DOC_TYPES)
        found = len(episode_files)

        if found == 0:
            context.logger.warning(f"No elastic documents found for {input_data.episode_id}")
            return self.__build_artifact(input_data, output_path)

        if found < expected and not self.config.allow_partial:
            missing = [folder for folder, _ in ELASTIC_DOC_TYPES if folder not in episode_files]
            context.logger.warning(
                f"Skipping {input_data.episode_id}: incomplete documents "
                f"({found}/{expected}), missing: {missing}. Set allow_partial=True to archive anyway.",
            )
            return self.__build_artifact(input_data, output_path)

        self.__create_archive(output_path, episode_files, context)

        return self.__build_artifact(input_data, output_path)

    def get_output_descriptors(self) -> List[FileOutput]:
        return [
            FileOutput(
                pattern="{season}/{episode}.zip",
                subdir="archives",
                min_size_bytes=1024 * 100,
            ),
        ]

    def _get_cache_path(
        self, input_data: ProcessedEpisode, context: ExecutionContext,
    ) -> Path:
        return self._get_standard_cache_path(input_data, context)

    def _load_from_cache(
        self,
        cache_path: Path,
        input_data: ProcessedEpisode,
        context: ExecutionContext,
    ) -> ArchiveArtifact:
        return self.__build_artifact(input_data, cache_path)

    @staticmethod
    def __collect_episode_files(
        context: ExecutionContext, episode_info: EpisodeInfo,
    ) -> Dict[str, Path]:
        elastic_dir = context.base_output_dir / "elastic_documents"
        season = episode_info.season_code()
        episode = episode_info.episode_code()

        collected: Dict[str, Path] = {}
        for folder, suffix in ELASTIC_DOC_TYPES:
            file_path = elastic_dir / folder / season / f"{episode}_{suffix}.jsonl"
            if file_path.exists():
                collected[folder] = file_path
        return collected

    @staticmethod
    def __create_archive(
        archive_path: Path,
        files: Dict[str, Path],
        context: ExecutionContext,
    ) -> None:
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = archive_path.with_suffix(archive_path.suffix + ".tmp")

        try:
            with zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for file_path in files.values():
                    zipf.write(file_path, arcname=file_path.name)

            temp_path.replace(archive_path)

            size_mb = archive_path.stat().st_size / (1024 * 1024)
            context.logger.info(
                f"Created archive: {archive_path.name} ({len(files)} files, {size_mb:.2f} MB)",
            )

        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            raise RuntimeError(f"Failed to create archive {archive_path}: {e}") from e

    @staticmethod
    def __build_artifact(
        input_data: ProcessedEpisode, output_path: Path,
    ) -> ArchiveArtifact:
        return ArchiveArtifact(
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            path=output_path,
        )
