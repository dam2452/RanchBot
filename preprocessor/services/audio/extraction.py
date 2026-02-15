from pathlib import Path
import subprocess
from typing import List

from preprocessor.config.step_configs import AudioExtractionConfig
from preprocessor.core.artifacts import (
    AudioArtifact,
    SourceVideo,
)
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext


class AudioExtractionStep(PipelineStep[SourceVideo, AudioArtifact, AudioExtractionConfig]):
    @property
    def name(self) -> str:
        return 'audio_extraction'

    def execute(self, input_data: SourceVideo, context: ExecutionContext) -> AudioArtifact:
        output_path = self.__resolve_output_path(input_data, context)

        if self.__is_cached(input_data, output_path, context):
            context.logger.info(f'Skipping {input_data.episode_id} (cached audio)')
            return self.__create_artifact(input_data, output_path)

        context.logger.info(f'Extracting audio for {input_data.episode_id}')
        context.mark_step_started(self.name, input_data.episode_id)

        self.__extract_audio(input_data.path, output_path, context)

        context.mark_step_completed(self.name, input_data.episode_id)
        return self.__create_artifact(input_data, output_path)

    def __resolve_output_path(self, input_data: SourceVideo, context: ExecutionContext) -> Path:
        episode_code = input_data.episode_info.episode_code()
        output_filename = f'{context.series_name}_{episode_code}.{self.config.format}'

        return context.get_output_path(
            input_data.episode_info,
            'extracted_audio',
            output_filename,
        )

    def __is_cached(
            self, input_data: SourceVideo, output_path: Path, context: ExecutionContext,
    ) -> bool:
        if not output_path.exists() or context.force_rerun:
            return False

        return context.is_step_completed(self.name, input_data.episode_id)

    def __extract_audio(
            self, input_path: Path, output_path: Path, context: ExecutionContext,
    ) -> None:
        command = self.__build_ffmpeg_command(input_path, output_path)

        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as e:
            context.logger.error(f'FFmpeg audio extraction failed: {e}')
            if output_path.exists():
                output_path.unlink()
            raise

    def __build_ffmpeg_command(self, input_path: Path, output_path: Path) -> List[str]:
        return [
            'ffmpeg', '-y', '-v', 'error',
            '-i', str(input_path),
            '-vn',  # Disable video processing
            '-acodec', 'pcm_s16le',
            '-ar', str(self.config.sample_rate),
            '-ac', str(self.config.channels),
            str(output_path),
        ]

    def __create_artifact(self, input_data: SourceVideo, output_path: Path) -> AudioArtifact:
        return AudioArtifact(
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            path=output_path,
            format=self.config.format,
        )
