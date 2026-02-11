from datetime import datetime

from preprocessor.config.step_configs import TextAnalysisConfig
from preprocessor.core.artifacts import (
    TextAnalysisResults,
    TranscriptionData,
)
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.lib.io.files import (
    atomic_write_json,
    load_json,
)
from preprocessor.lib.text.text_statistics import TextStatistics


class TextAnalysisStep(PipelineStep[TranscriptionData, TextAnalysisResults, TextAnalysisConfig]):

    def execute(self, input_data: TranscriptionData, context: ExecutionContext) -> TextAnalysisResults:
        output_filename = input_data.path.stem + '_text_stats.json'
        output_path = input_data.path.parent / output_filename
        if output_path.exists() and (not context.force_rerun):
            if context.is_step_completed(self.name, input_data.episode_id):
                context.logger.info(f'Skipping {input_data.episode_id} (cached)')
                stats_data = load_json(output_path)
                return TextAnalysisResults(episode_id=input_data.episode_id, episode_info=input_data.episode_info, path=output_path, statistics=stats_data)
        context.logger.info(f'Analyzing text for {input_data.episode_id}')
        context.mark_step_started(self.name, input_data.episode_id)
        txt_path = input_data.path
        if input_data.format != 'txt':
            txt_path = input_data.path.with_suffix('.txt')
        if not txt_path.exists():
            raise FileNotFoundError(f'Transcription text file not found: {txt_path}')
        stats = TextStatistics.from_file(txt_path, language=self.config.language)
        result_data = {
            'metadata': {
                'episode_id': input_data.episode_id,
                'language': self.config.language,
                'source_file': txt_path.name,
                'analyzed_at': datetime.now().isoformat(),
            },
            **stats.to_dict(),
        }
        atomic_write_json(output_path, result_data)
        context.mark_step_completed(self.name, input_data.episode_id)
        return TextAnalysisResults(episode_id=input_data.episode_id, episode_info=input_data.episode_info, path=output_path, statistics=result_data)

    @property
    def name(self) -> str:
        return 'text_analysis'
