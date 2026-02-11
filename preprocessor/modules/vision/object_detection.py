from pathlib import Path

from preprocessor.config.step_configs import ObjectDetectionConfig
from preprocessor.core.artifacts import (
    FrameCollection,
    ObjectDetectionData,
)
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext


class ObjectDetectionStep(PipelineStep[FrameCollection, ObjectDetectionData, ObjectDetectionConfig]):

    def execute(self, input_data: FrameCollection, context: ExecutionContext) -> ObjectDetectionData:
        output_filename: str = f'{context.series_name}_{input_data.episode_info.episode_code()}_objects.json'
        output_path: Path = context.get_output_path(input_data.episode_info, 'object_detections', output_filename)
        if output_path.exists() and (not context.force_rerun):
            if context.is_step_completed(self.name, input_data.episode_id):
                context.logger.info(f'Skipping {input_data.episode_id} (cached object detection)')
                return ObjectDetectionData(episode_id=input_data.episode_id, episode_info=input_data.episode_info, path=output_path)
        context.logger.info(f'Detecting objects for {input_data.episode_id}')
        context.mark_step_started(self.name, input_data.episode_id)
        context.mark_step_completed(self.name, input_data.episode_id)
        return ObjectDetectionData(episode_id=input_data.episode_id, episode_info=input_data.episode_info, path=output_path)

    @property
    def name(self) -> str:
        return 'object_detection'
