from pathlib import Path
from typing import (
    Any,
    Dict,
    Optional,
)

from preprocessor.config.step_configs import WhisperTranscriptionConfig
from preprocessor.core.artifacts import (
    AudioArtifact,
    TranscriptionData,
)
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.lib.episodes.episode_manager import EpisodeManager
from preprocessor.lib.io.files import atomic_write_json
from preprocessor.lib.transcription.whisper import Whisper


class TranscriptionStep(PipelineStep[AudioArtifact, TranscriptionData, WhisperTranscriptionConfig]):

    def __init__(self, config: WhisperTranscriptionConfig) -> None:
        super().__init__(config)
        self._whisper: Optional[Whisper] = None

    def cleanup(self) -> None:
        if self._whisper:
            self._whisper.cleanup()
            self._whisper = None

    def execute(self, input_data: AudioArtifact, context: ExecutionContext) -> TranscriptionData:
        output_filename: str = (
            f'{context.series_name}_{input_data.episode_info.episode_code()}.json'
        )
        output_path: Path = context.get_output_path(
            input_data.episode_info,
            'transcriptions',
            f'raw/{output_filename}',
        )

        if output_path.exists() and (not context.force_rerun):
            if context.is_step_completed(self.name, input_data.episode_id):
                context.logger.info(f'Skipping {input_data.episode_id} (cached transcription)')
                return TranscriptionData(
                    episode_id=input_data.episode_id,
                    episode_info=input_data.episode_info,
                    path=output_path,
                    language=self.config.language,
                    model=self.config.model,
                    format='json',
                )

        if self._whisper is None:
            self._whisper = Whisper(
                model=self.config.model,
                language=self.config.language,
                device=self.config.device,
                beam_size=self.config.beam_size,
            )

        context.logger.info(
            f'Transcribing {input_data.episode_id} using Whisper {self.config.model}',
        )
        context.mark_step_started(self.name, input_data.episode_id)

        try:
            result: Dict[str, Any] = self._whisper.transcribe(input_data.path)
            result['episode_info'] = EpisodeManager.get_metadata(input_data.episode_info)
            atomic_write_json(output_path, result)
        except Exception as e:
            context.logger.error(
                f'Whisper transcription failed for {input_data.episode_id}: {e}',
            )
            if output_path.exists():
                output_path.unlink()
            raise

        context.mark_step_completed(self.name, input_data.episode_id)
        return TranscriptionData(
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            path=output_path,
            language=result.get('language', self.config.language),
            model=self.config.model,
            format='json',
        )

    @property
    def name(self) -> str:
        return 'transcription'
