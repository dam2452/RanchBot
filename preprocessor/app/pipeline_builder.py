from pathlib import Path
from typing import (
    Any,
    List,
)

from preprocessor.core.artifacts import SourceVideo
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.lib.episodes.episode_manager import EpisodeManager


class Pipeline:
    def __init__(self, context: ExecutionContext):
        self.context = context
        self.steps: List[PipelineStep] = []

    def add_step(self, step: PipelineStep) -> "Pipeline":
        self.steps.append(step)
        return self

    def run_for_episodes(
        self, source_path: Path, episode_manager: EpisodeManager,
    ) -> None:
        video_files = self.__discover_videos(source_path)
        self.context.logger.info(
            f"Discovered {len(video_files)} video files in {source_path}",
        )

        current_artifacts: List[Any] = []
        for video_file in video_files:
            episode_info = episode_manager.parse_filename(video_file)
            if not episode_info:
                self.context.logger.warning(f"Cannot parse: {video_file}")
                continue

            episode_id = episode_manager.get_episode_id_for_state(episode_info)
            current_artifacts.append(
                SourceVideo(
                    path=video_file,
                    episode_id=episode_id,
                    episode_info=episode_info,
                ),
            )

        for step in self.steps:
            self.context.logger.info(f"=== Running Step: {step.name} ===")
            next_artifacts = []

            for artifact in current_artifacts:
                episode_id = artifact.episode_id

                if self.__should_skip_step(step.name, episode_id):
                    self.context.logger.info(
                        f"⏭️  Skipping {step.name} for {episode_id} (already completed)",
                    )
                    next_artifacts.append(artifact)
                    continue

                try:
                    self.__mark_step_in_progress(step.name, episode_id)
                    result = step.execute(artifact, self.context)
                    self.__mark_step_completed(step.name, episode_id)

                    if result:
                        next_artifacts.append(result)
                    else:
                        next_artifacts.append(artifact)
                except Exception as e:
                    self.context.logger.error(
                        f"Step {step.name} failed for {artifact.episode_id}: {e}",
                    )
                    raise

            current_artifacts = next_artifacts

    def __should_skip_step(self, step_name: str, episode_id: str) -> bool:
        if self.context.force_rerun:
            return False

        if self.context.state_manager is None:
            return False

        return self.context.state_manager.is_step_completed(step_name, episode_id)

    def __mark_step_in_progress(self, step_name: str, episode_id: str) -> None:
        if self.context.state_manager is None:
            return
        self.context.state_manager.mark_step_started(step_name, episode_id)

    def __mark_step_completed(self, step_name: str, episode_id: str) -> None:
        if self.context.state_manager is None:
            return
        self.context.state_manager.mark_step_completed(step_name, episode_id)

    @staticmethod
    def __discover_videos(source_path: Path) -> List[Path]:
        extensions = ["*.mp4", "*.mkv", "*.avi"]
        videos = []
        for ext in extensions:
            videos.extend(source_path.glob(f"**/{ext}"))
        return sorted(videos)

    def cleanup(self) -> None:
        for step in self.steps:
            if hasattr(step, "cleanup"):
                try:
                    step.cleanup()
                except Exception as e:
                    self.context.logger.error(f"Cleanup failed for step {step.name}: {e}")
