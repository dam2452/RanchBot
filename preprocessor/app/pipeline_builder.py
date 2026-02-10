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
                try:
                    result = step.execute(artifact, self.context)
                    if result:
                        next_artifacts.append(result)
                except Exception as e:
                    self.context.logger.error(
                        f"Step {step.name} failed for {artifact.episode_id}: {e}",
                    )

            current_artifacts = next_artifacts

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
