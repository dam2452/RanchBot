from datetime import datetime
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
)

from preprocessor.config.step_configs import TextAnalysisConfig
from preprocessor.core.artifacts import (
    TextAnalysisResults,
    TranscriptionData,
)
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.core.output_descriptors import (
    JsonFileOutput,
    OutputDescriptor,
)
from preprocessor.services.io.files import FileOperations
from preprocessor.services.text.text_statistics import TextStatistics


class TextAnalysisStep(PipelineStep[TranscriptionData, TextAnalysisResults, TextAnalysisConfig]):
    @property
    def supports_batch_processing(self) -> bool:
        return True

    def execute_batch(
        self, input_data: List[TranscriptionData], context: ExecutionContext,
    ) -> List[TextAnalysisResults]:
        return self._execute_with_threadpool(
            input_data, context, self.config.max_parallel_episodes, self.execute,
        )

    def _process(
        self, input_data: TranscriptionData, context: ExecutionContext,
    ) -> TextAnalysisResults:
        output_path = self._get_cache_path(input_data, context)

        txt_path = self.__resolve_text_file_path(input_data)
        stats = self.__analyze_text_statistics(txt_path)
        result_data = self.__build_result_payload(stats, txt_path, input_data)

        FileOperations.atomic_write_json(output_path, result_data)

        return self.__construct_analysis_results(input_data, output_path, result_data)

    def get_output_descriptors(self) -> List[OutputDescriptor]:
        return [
            JsonFileOutput(
                pattern="{season}/{episode}.json",
                subdir="text_analysis",
                min_size_bytes=50,
            ),
        ]

    def _get_cache_path(
        self, input_data: TranscriptionData, context: ExecutionContext,
    ) -> Path:
        return self._get_standard_cache_path(input_data, context)

    def _load_from_cache(
        self, cache_path: Path, input_data: TranscriptionData, context: ExecutionContext,
    ) -> TextAnalysisResults:
        stats_data = FileOperations.load_json(cache_path)
        return self.__construct_analysis_results(input_data, cache_path, stats_data)

    def __analyze_text_statistics(self, txt_path: Path) -> TextStatistics:
        return TextStatistics.from_file(txt_path, language=self.config.language)

    def __build_result_payload(
        self,
        stats: TextStatistics,
        txt_path: Path,
        input_data: TranscriptionData,
    ) -> Dict[str, Any]:
        return {
            'metadata': {
                'episode_id': input_data.episode_id,
                'language': self.config.language,
                'source_file': txt_path.name,
                'analyzed_at': datetime.now().isoformat(),
            },
            **stats.to_dict(),
        }

    @staticmethod
    def __resolve_text_file_path(input_data: TranscriptionData) -> Path:
        txt_path = input_data.path
        if input_data.format != 'txt':
            txt_path = input_data.path.with_suffix('.txt')

        if not txt_path.exists():
            raise FileNotFoundError(f'Transcription text file not found: {txt_path}')

        return txt_path

    @staticmethod
    def __construct_analysis_results(
        input_data: TranscriptionData,
        output_path: Path,
        result_data: Dict[str, Any],
    ) -> TextAnalysisResults:
        return TextAnalysisResults(
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            path=output_path,
            statistics=result_data,
        )
