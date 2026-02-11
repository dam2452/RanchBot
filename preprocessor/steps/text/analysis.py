from datetime import datetime
from pathlib import Path
from typing import (
    Any,
    Dict,
)

from preprocessor.config.step_configs import TextAnalysisConfig
from preprocessor.core.artifacts import (
    TextAnalysisResults,
    TranscriptionData,
)
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.services.io.files import (
    atomic_write_json,
    load_json,
)
from preprocessor.services.text.text_statistics import TextStatistics


class TextAnalysisStep(PipelineStep[TranscriptionData, TextAnalysisResults, TextAnalysisConfig]):

    def execute(self, input_data: TranscriptionData, context: ExecutionContext) -> TextAnalysisResults:
        output_path = self._get_output_path(input_data)

        if self._should_skip_processing(output_path, context, input_data):
            return self._load_cached_result(output_path, input_data)

        context.logger.info(f'Analyzing text for {input_data.episode_id}')
        context.mark_step_started(self.name, input_data.episode_id)

        txt_path = self._get_text_file_path(input_data)
        stats = self._analyze_text_statistics(txt_path)
        result_data = self._build_result_data(stats, txt_path, input_data)

        atomic_write_json(output_path, result_data)
        context.mark_step_completed(self.name, input_data.episode_id)

        return TextAnalysisResults(
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            path=output_path,
            statistics=result_data,
        )

    @property
    def name(self) -> str:
        return 'text_analysis'

    @staticmethod
    def _get_output_path(input_data: TranscriptionData) -> Path:
        output_filename = input_data.path.stem + '_text_stats.json'
        return input_data.path.parent / output_filename

    def _should_skip_processing(
        self,
        output_path: Path,
        context: ExecutionContext,
        input_data: TranscriptionData,
    ) -> bool:
        if output_path.exists() and (not context.force_rerun):
            if context.is_step_completed(self.name, input_data.episode_id):
                context.logger.info(f'Skipping {input_data.episode_id} (cached)')
                return True
        return False

    @staticmethod
    def _load_cached_result(output_path: Path, input_data: TranscriptionData) -> TextAnalysisResults:
        stats_data = load_json(output_path)
        return TextAnalysisResults(
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            path=output_path,
            statistics=stats_data,
        )

    @staticmethod
    def _get_text_file_path(input_data: TranscriptionData) -> Path:
        txt_path = input_data.path
        if input_data.format != 'txt':
            txt_path = input_data.path.with_suffix('.txt')
        if not txt_path.exists():
            raise FileNotFoundError(f'Transcription text file not found: {txt_path}')
        return txt_path

    def _analyze_text_statistics(self, txt_path: Path) -> TextStatistics:
        return TextStatistics.from_file(txt_path, language=self.config.language)

    def _build_result_data(
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
