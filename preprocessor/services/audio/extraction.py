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

    def execute(self, input_data: SourceVideo, context: ExecutionContext) -> AudioArtifact:
        episode_code = input_data.episode_info.episode_code()
        output_filename: str = (
            f'{context.series_name}_{episode_code}.{self.config.format}'
        )
        output_path: Path = context.get_output_path(
            input_data.episode_info,
            'extracted_audio',
            output_filename,
        )
        if output_path.exists() and (not context.force_rerun):
            if context.is_step_completed(self.name, input_data.episode_id):
                context.logger.info(f'Skipping {input_data.episode_id} (cached audio)')
                return AudioArtifact(
                    episode_id=input_data.episode_id,
                    episode_info=input_data.episode_info,
                    path=output_path,
                    format=self.config.format,
                )
        context.logger.info(f'Extracting audio for {input_data.episode_id}')
        context.mark_step_started(self.name, input_data.episode_id)
        command: List[str] = [
            'ffmpeg', '-y', '-v', 'error',
            '-i', str(input_data.path),
            '-vn',
            '-acodec', 'pcm_s16le',
            '-ar', str(self.config.sample_rate),
            '-ac', str(self.config.channels),
            str(output_path),
        ]
        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as e:
            context.logger.error(f'FFmpeg audio extraction failed: {e}')
            if output_path.exists():
                output_path.unlink()
            raise
        context.mark_step_completed(self.name, input_data.episode_id)
        return AudioArtifact(
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            path=output_path,
            format=self.config.format,
        )

    @property
    def name(self) -> str:
        return 'audio_extraction'
