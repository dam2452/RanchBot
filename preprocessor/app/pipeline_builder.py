from __future__ import annotations

from pathlib import Path
from typing import (
    Any,
    List,
)

from preprocessor.app.pipeline import PipelineDefinition
from preprocessor.core.artifacts import SourceVideo
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.services.episodes.episode_manager import EpisodeManager
from preprocessor.services.video.discovery import VideoDiscovery


class PipelineExecutor:
    def __init__(self, context: ExecutionContext) -> None:
        self.__context = context
        self.__steps: List[PipelineStep] = []

    def add_step(self, step: PipelineStep) -> "PipelineExecutor":
        self.__steps.append(step)
        return self

    def cleanup(self) -> None:
        for step in self.__steps:
            if hasattr(step, "cleanup"):
                try:
                    step.cleanup()
                except Exception as e:
                    self.__context.logger.error(f"Cleanup failed for step {step.name}: {e}")

    def execute_step(
        self,
        pipeline: "PipelineDefinition",
        step_id: str,
        source_path: Path,
        episode_manager: EpisodeManager,
    ) -> None:
        step_def = pipeline.get_step(step_id)
        self.__context.logger.info(f"Step: {step_id}")
        self.__context.logger.info(f"{step_def.description}")

        instance = step_def.step_class(step_def.config)

        runner = PipelineExecutor(self.__context)
        runner.add_step(instance)
        runner.run(source_path, episode_manager)

        self.__context.logger.info(f"Step '{step_id}' completed")

    def execute_steps(
        self,
        pipeline: "PipelineDefinition",
        step_ids: List[str],
        source_path: Path,
        episode_manager: EpisodeManager,
    ) -> None:
        for step_id in step_ids:
            self.__context.logger.info(f"{'=' * 80}")
            self.execute_step(pipeline, step_id, source_path, episode_manager)

    def run(self, source_path: Path, episode_manager: EpisodeManager) -> None:
        video_files = VideoDiscovery.discover(source_path)
        self.__context.logger.info(
            f"Discovered {len(video_files)} video files in {source_path}",
        )

        current_artifacts: List[Any] = []
        for video_file in video_files:
            episode_info = episode_manager.parse_filename(video_file)
            if not episode_info:
                self.__context.logger.warning(f"Cannot parse: {video_file}")
                continue

            episode_id = episode_manager.get_episode_id_for_state(episode_info)
            current_artifacts.append(
                SourceVideo(
                    path=video_file,
                    episode_id=episode_id,
                    episode_info=episode_info,
                ),
            )

        for step in self.__steps:
            if step.is_global:
                self.__run_global_step(step)
            else:
                current_artifacts = self.__run_episode_step(step, current_artifacts)

    def __run_global_step(self, step: PipelineStep) -> None:
        self.__context.logger.info(f"=== Running Global Step: {step.name} ===")

        if self.__should_skip_step(step.name, 'all'):
            self.__context.logger.info(f"Skipping {step.name} (already completed)")
            return

        try:
            self.__mark_step_in_progress(step.name, 'all')
            step.execute(None, self.__context)
            self.__mark_step_completed(step.name, 'all')
        except Exception as e:
            self.__context.logger.error(f"Global step {step.name} failed: {e}")
            raise

    def __run_episode_step(
        self, step: PipelineStep, current_artifacts: List[Any],
    ) -> List[Any]:
        self.__context.logger.info(f"=== Running Step: {step.name} ===")

        if self.__should_use_batch_processing(step):
            return self.__run_episode_step_batch(step, current_artifacts)
        return self.__run_episode_step_sequential(step, current_artifacts)

    def __should_use_batch_processing(self, step: PipelineStep) -> bool:

        if self.__context.disable_parallel:
            self.__context.logger.info(
                f"Batch processing disabled globally for {step.name}",
            )
            return False

        if hasattr(step.config, 'enable_parallel'):
            if not step.config.enable_parallel:
                self.__context.logger.info(
                    f"Batch processing disabled by config for {step.name}",
                )
                return False

        if not step.supports_batch_processing:
            return False

        return True

    def __run_episode_step_sequential(
        self, step: PipelineStep, current_artifacts: List[Any],
    ) -> List[Any]:
        next_artifacts = []

        for artifact in current_artifacts:
            episode_id = artifact.episode_id

            if self.__should_skip_step(step.name, episode_id):
                self.__context.logger.info(
                    f"Skipping {step.name} for {episode_id} (already completed)",
                )
                next_artifacts.append(artifact)
                continue

            try:
                self.__mark_step_in_progress(step.name, episode_id)
                result = step.execute(artifact, self.__context)
                self.__mark_step_completed(step.name, episode_id)

                if result:
                    next_artifacts.append(result)
                else:
                    next_artifacts.append(artifact)
            except Exception as e:
                self.__context.logger.error(
                    f"Step {step.name} failed for {artifact.episode_id}: {e}",
                )
                raise

        return next_artifacts

    def __run_episode_step_batch(
        self, step: PipelineStep, current_artifacts: List[Any],
    ) -> List[Any]:
        artifacts_to_process = []
        next_artifacts = []

        for artifact in current_artifacts:
            episode_id = artifact.episode_id
            if self.__should_skip_step(step.name, episode_id):
                self.__context.logger.info(
                    f"Skipping {step.name} for {episode_id} (already completed)",
                )
                next_artifacts.append(artifact)
            else:
                artifacts_to_process.append(artifact)

        if not artifacts_to_process:
            return next_artifacts

        self.__context.logger.info(
            f"Processing {len(artifacts_to_process)} episodes with batch processing",
        )

        try:
            if hasattr(step, 'setup_resources'):
                step.setup_resources(self.__context)

            for artifact in artifacts_to_process:
                self.__mark_step_in_progress(step.name, artifact.episode_id)

            results = step.execute_batch(artifacts_to_process, self.__context)

            for artifact, result in zip(artifacts_to_process, results):
                self.__mark_step_completed(step.name, artifact.episode_id)
                next_artifacts.append(result or artifact)

            return next_artifacts

        finally:
            if hasattr(step, 'teardown_resources'):
                step.teardown_resources(self.__context)

    def __mark_step_completed(self, step_name: str, episode_id: str) -> None:
        if self.__context.state_manager is None:
            return
        self.__context.state_manager.mark_step_completed(step_name, episode_id)

    def __mark_step_in_progress(self, step_name: str, episode_id: str) -> None:
        if self.__context.state_manager is None:
            return
        self.__context.state_manager.mark_step_started(step_name, episode_id)

    def __should_skip_step(self, step_name: str, episode_id: str) -> bool:
        if self.__context.force_rerun:
            return False

        if self.__context.state_manager is None:
            return False

        return self.__context.state_manager.is_step_completed(step_name, episode_id)
