from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from preprocessor.config.step_configs import WhisperTranscriptionConfig
from preprocessor.core.artifacts import (
    TranscodedVideo,
    TranscriptionData,
)
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.core.output_descriptors import JsonFileOutput
from preprocessor.services.episodes.episode_manager import EpisodeManager
from preprocessor.services.io.files import FileOperations
from preprocessor.services.transcription.whisper import Whisper


class TranscriptionStep(
    PipelineStep[TranscodedVideo, TranscriptionData, WhisperTranscriptionConfig],
):
    def __init__(self, config: WhisperTranscriptionConfig) -> None:
        super().__init__(config)
        self.__whisper: Optional[Whisper] = None

    @property
    def supports_batch_processing(self) -> bool:
        return True

    def setup_resources(self, context: ExecutionContext) -> None:
        if self.__whisper is None:
            self.__load_whisper(context)

    def teardown_resources(self, context: ExecutionContext) -> None:
        if self.__whisper:
            self.__unload_whisper(context)

    def cleanup(self) -> None:
        self.__unload_whisper()

    def execute_batch(
            self, input_data: List[TranscodedVideo], context: ExecutionContext,
    ) -> List[TranscriptionData]:
        return self._execute_with_threadpool(
            input_data, context, self.config.max_parallel_episodes, self.execute,
        )

    def _process(
            self, input_data: TranscodedVideo, context: ExecutionContext,
    ) -> TranscriptionData:
        output_path = self._get_cache_path(input_data, context)

        if self.__whisper is None:
            self.__load_whisper(context)

        result = self.__transcribe_and_save(input_data, output_path, context)

        return self.__construct_result_artifact(output_path, input_data, result)

    def get_output_descriptors(self) -> List[JsonFileOutput]:
        return [
            JsonFileOutput(
                pattern="{season}/{episode}.json",
                subdir="transcriptions",
                min_size_bytes=50,
            ),
        ]

    def _get_cache_path(
            self, input_data: TranscodedVideo, context: ExecutionContext,
    ) -> Path:
        return self._get_standard_cache_path(input_data, context)

    def _load_from_cache(
            self,
            cache_path: Path,
            input_data: TranscodedVideo,
            context: ExecutionContext,
    ) -> TranscriptionData:
        return TranscriptionData(
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            path=cache_path,
            language=self.config.language,
            model=self.config.model,
            format='json',
        )

    def __load_whisper(self, context: Optional[ExecutionContext] = None) -> None:
        if context:
            context.logger.info(f'Loading Whisper model: {self.config.model}')

        self.__whisper = Whisper(
            model=self.config.model,
            language=self.config.language,
            device=self.config.device,
            beam_size=self.config.beam_size,
        )

    def __unload_whisper(self, context: Optional[ExecutionContext] = None) -> None:
        if self.__whisper:
            self.__whisper.cleanup()
            self.__whisper = None
            if context:
                context.logger.info('Whisper model unloaded')

    def __transcribe_and_save(
            self,
            input_data: TranscodedVideo,
            output_path: Path,
            context: ExecutionContext,
    ) -> Dict[str, Any]:
        try:
            if self.__whisper is None:
                raise RuntimeError("Whisper model not initialized")

            result: Dict[str, Any] = self.__whisper.transcribe(input_data.path)
            result['episode_info'] = EpisodeManager.get_metadata(
                input_data.episode_info,
            )
            FileOperations.atomic_write_json(output_path, result)
            return result
        except Exception as e:
            context.logger.error(
                f'Whisper transcription failed for {input_data.episode_id}: {e}',
            )
            if output_path.exists():
                output_path.unlink()
            raise

    def __construct_result_artifact(
            self,
            output_path: Path,
            input_data: TranscodedVideo,
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
