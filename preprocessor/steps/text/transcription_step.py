from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
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
from preprocessor.services.io.files import FileOperations
from preprocessor.services.transcription.whisper import Whisper


class TranscriptionStep(PipelineStep[AudioArtifact, TranscriptionData, WhisperTranscriptionConfig]):
    def __init__(self, config: WhisperTranscriptionConfig) -> None:
        super().__init__(config)
        self.__whisper: Optional[Whisper] = None

    @property
    def name(self) -> str:
        return 'transcription'

    @property
    def supports_batch_processing(self) -> bool:
        return True

    def setup_resources(self, context: ExecutionContext) -> None:
        if self.__whisper is None:
            context.logger.info(f'Loading Whisper model: {self.config.model}')
            self.__whisper = Whisper(
                model=self.config.model,
                language=self.config.language,
                device=self.config.device,
                beam_size=self.config.beam_size,
            )

    def execute_batch(
        self, input_data: List[AudioArtifact], context: ExecutionContext,
    ) -> List[TranscriptionData]:
        return self._execute_with_threadpool(
            input_data, context, self.config.max_parallel_episodes, self.__execute_single,
        )

    def teardown_resources(self, context: ExecutionContext) -> None:
        if self.__whisper:
            self.__whisper.cleanup()
            self.__whisper = None
            context.logger.info('Whisper model unloaded')

    def cleanup(self) -> None:
        if self.__whisper:
            self.__whisper.cleanup()
            self.__whisper = None

    def execute(self, input_data: AudioArtifact, context: ExecutionContext) -> TranscriptionData:
        output_path = self.__resolve_output_path(input_data, context)

        if self._check_cache_validity(output_path, context, input_data.episode_id, 'cached transcription'):
            return self.__construct_cached_result(output_path, input_data)

        self.__prepare_whisper_model()
        context.logger.info(
            f'Transcribing {input_data.episode_id} using Whisper {self.config.model}',
        )
        context.mark_step_started(self.name, input_data.episode_id)

        result = self.__process_audio_transcription(input_data, output_path, context)

        context.mark_step_completed(self.name, input_data.episode_id)
        return self.__construct_result_artifact(output_path, input_data, result)

    def __execute_single(
        self, input_data: AudioArtifact, context: ExecutionContext,
    ) -> TranscriptionData:
        output_path = self.__resolve_output_path(input_data, context)

        if self._check_cache_validity(output_path, context, input_data.episode_id, 'cached transcription'):
            return self.__construct_cached_result(output_path, input_data)

        context.logger.info(
            f'Transcribing {input_data.episode_id} using Whisper {self.config.model}',
        )
        context.mark_step_started(self.name, input_data.episode_id)

        result = self.__process_audio_transcription(input_data, output_path, context)

        context.mark_step_completed(self.name, input_data.episode_id)
        return self.__construct_result_artifact(output_path, input_data, result)

    def __prepare_whisper_model(self) -> None:
        if self.__whisper is None:
            self.__whisper = Whisper(
                model=self.config.model,
                language=self.config.language,
                device=self.config.device,
                beam_size=self.config.beam_size,
            )

    def __process_audio_transcription(
            self,
            input_data: AudioArtifact,
            output_path: Path,
            context: ExecutionContext,
    ) -> Dict[str, Any]:
        try:
            result: Dict[str, Any] = self.__whisper.transcribe(input_data.path)
            result['episode_info'] = EpisodeManager.get_metadata(input_data.episode_info)
            FileOperations.atomic_write_json(output_path, result)
            return result
        except Exception as e:
            context.logger.error(
                f'Whisper transcription failed for {input_data.episode_id}: {e}',
            )
            if output_path.exists():
                output_path.unlink()
            raise

    def __construct_cached_result(
            self, output_path: Path, input_data: AudioArtifact,
    ) -> TranscriptionData:
        return TranscriptionData(
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            path=output_path,
            language=self.config.language,
            model=self.config.model,
            format='json',
        )

    def __construct_result_artifact(
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

    @staticmethod
    def __resolve_output_path(input_data: AudioArtifact, context: ExecutionContext) -> Path:
        output_filename: str = (
            f'{context.series_name}_{input_data.episode_info.episode_code()}.json'
        )
        return context.get_output_path(
            input_data.episode_info,
            'transcriptions',
            f'raw/{output_filename}',
        )
