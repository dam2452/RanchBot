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
from preprocessor.services.episodes.episode_manager import EpisodeManager
from preprocessor.services.io.files import atomic_write_json
from preprocessor.services.transcription.whisper import Whisper


class TranscriptionStep(PipelineStep[AudioArtifact, TranscriptionData, WhisperTranscriptionConfig]):

    def __init__(self, config: WhisperTranscriptionConfig) -> None:
        super().__init__(config)
        self._whisper: Optional[Whisper] = None

    def cleanup(self) -> None:
        if self._whisper:
            self._whisper.cleanup()
            self._whisper = None

    def execute(self, input_data: AudioArtifact, context: ExecutionContext) -> TranscriptionData:
        output_path = self._get_output_path(input_data, context)

        if self._check_cache_validity(output_path, context, input_data.episode_id, 'cached transcription'):
            return self._create_cached_result(output_path, input_data)

        self._ensure_whisper_loaded()
        context.logger.info(
            f'Transcribing {input_data.episode_id} using Whisper {self.config.model}',
        )
        context.mark_step_started(self.name, input_data.episode_id)

        result = self._transcribe_audio(input_data, output_path, context)
        context.mark_step_completed(self.name, input_data.episode_id)

        return self._create_result_artifact(output_path, input_data, result)

    @property
    def name(self) -> str:
        return 'transcription'

    @staticmethod
    def _get_output_path(input_data: AudioArtifact, context: ExecutionContext) -> Path:
        output_filename: str = (
            f'{context.series_name}_{input_data.episode_info.episode_code()}.json'
        )
        return context.get_output_path(
            input_data.episode_info,
            'transcriptions',
            f'raw/{output_filename}',
        )


    def _create_cached_result(self, output_path: Path, input_data: AudioArtifact) -> TranscriptionData:
        return TranscriptionData(
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            path=output_path,
            language=self.config.language,
            model=self.config.model,
            format='json',
        )

    def _ensure_whisper_loaded(self) -> None:
        if self._whisper is None:
            self._whisper = Whisper(
                model=self.config.model,
                language=self.config.language,
                device=self.config.device,
                beam_size=self.config.beam_size,
            )

    def _transcribe_audio(
        self,
        input_data: AudioArtifact,
        output_path: Path,
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        try:
            result: Dict[str, Any] = self._whisper.transcribe(input_data.path)
            result['episode_info'] = EpisodeManager.get_metadata(input_data.episode_info)
            atomic_write_json(output_path, result)
            return result
        except Exception as e:
            context.logger.error(
                f'Whisper transcription failed for {input_data.episode_id}: {e}',
            )
            if output_path.exists():
                output_path.unlink()
            raise

    def _create_result_artifact(
        self,
        output_path: Path,
        input_data: AudioArtifact,
        result: Dict[str, Any],
    ) -> TranscriptionData:
        return TranscriptionData(
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            path=output_path,
            language=result.get('language', self.config.language),
            model=self.config.model,
            format='json',
        )
