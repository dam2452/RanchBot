import json
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from preprocessor.config.step_configs import TranscriptionConfig
from preprocessor.core.artifacts import (
    TranscodedVideo,
    TranscriptionData,
)
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.core.output_descriptors import JsonFileOutput
from preprocessor.services.episodes.episode_manager import EpisodeManager
from preprocessor.services.io.files import FileOperations
from preprocessor.services.transcription.engines.base_engine import TranscriptionEngine
from preprocessor.services.transcription.engines.elevenlabs_engine import ElevenLabsEngine
from preprocessor.services.transcription.engines.whisper_engine import WhisperEngine
from preprocessor.services.transcription.generators.json_generator import JsonGenerator
from preprocessor.services.transcription.generators.srt_generator import SrtGenerator
from preprocessor.services.transcription.generators.txt_generator import TxtGenerator


class TranscriptionStep(
    PipelineStep[TranscodedVideo, TranscriptionData, TranscriptionConfig],
):
    def __init__(self, config: TranscriptionConfig) -> None:
        super().__init__(config)
        self.__engine: Optional[TranscriptionEngine] = None

    @property
    def supports_batch_processing(self) -> bool:
        return True

    def setup_resources(self, context: ExecutionContext) -> None:
        if self.__engine is None:
            self.__engine = self.__create_engine(context)

    def teardown_resources(self, context: ExecutionContext) -> None:
        if self.__engine:
            self.__engine.cleanup()
            self.__engine = None
            context.logger.info('Transcription engine unloaded')

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

        if self.__engine is None:
            self.__engine = self.__create_engine(context)

        result = self.__transcribe_and_save(input_data, output_path, context)
        self.__save_additional_formats(output_path, result)

        return self.__construct_result_artifact(output_path, input_data, result)

    def get_output_descriptors(self) -> List[JsonFileOutput]:
        return [
            JsonFileOutput(
                pattern="{season}/{episode}/{episode}.json",
                subdir="",
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
        self.__ensure_additional_formats(cache_path)
        return TranscriptionData(
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            path=cache_path,
            language=self.config.language,
            model=self.config.model,
            format='json',
        )

    def __create_engine(self, context: ExecutionContext) -> TranscriptionEngine:
        if self.config.mode == '11labs':
            context.logger.info('Creating ElevenLabs transcription engine')
            return ElevenLabsEngine(logger=context.logger)

        context.logger.info(f'Loading Whisper model: {self.config.model}')
        return WhisperEngine(
            model_name=self.config.model,
            language=self.config.language,
            device=self.config.device,
            beam_size=self.config.beam_size,
            temperature=self.config.temperature,
        )

    def __transcribe_and_save(
            self,
            input_data: TranscodedVideo,
            output_path: Path,
            context: ExecutionContext,
    ) -> Dict[str, Any]:
        try:
            if self.__engine is None:
                raise RuntimeError('Transcription engine not initialized')

            result: Dict[str, Any] = self.__engine.transcribe(input_data.path)
            result['episode_info'] = EpisodeManager.get_metadata(
                input_data.episode_info,
            )
            FileOperations.atomic_write_json(output_path, result)
            return result
        except Exception as e:
            context.logger.error(
                f'Transcription failed for {input_data.episode_id}: {e}',
            )
            if output_path.exists():
                output_path.unlink()
            raise

    @staticmethod
    def __save_additional_formats(output_path: Path, data: Dict[str, Any]) -> None:
        stem = output_path.stem
        parent = output_path.parent

        simple = JsonGenerator.convert_to_simple_format(data)
        (parent / f'{stem}_simple.json').write_text(
            json.dumps(simple, indent=2, ensure_ascii=False), encoding='utf-8',
        )
        (parent / f'{stem}.srt').write_text(
            SrtGenerator.convert_to_srt_format(data), encoding='utf-8',
        )
        (parent / f'{stem}.txt').write_text(
            TxtGenerator.convert_to_txt_format(data), encoding='utf-8',
        )

    @staticmethod
    def __ensure_additional_formats(cache_path: Path) -> None:
        stem = cache_path.stem
        parent = cache_path.parent
        missing = any(
            not (parent / name).exists()
            for name in (f'{stem}_simple.json', f'{stem}.srt', f'{stem}.txt')
        )
        if not missing:
            return
        data = FileOperations.load_json(cache_path)
        TranscriptionStep.__save_additional_formats(cache_path, data)

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
