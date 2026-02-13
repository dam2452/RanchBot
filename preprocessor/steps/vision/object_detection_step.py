from pathlib import Path

from preprocessor.config.step_configs import ObjectDetectionConfig
from preprocessor.core.artifacts import (
    FrameCollection,
    ObjectDetectionData,
)
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext


class ObjectDetectionStep(PipelineStep[FrameCollection, ObjectDetectionData, ObjectDetectionConfig]):
    @property
    def name(self) -> str:
        return 'object_detection'

    def execute(
        self, input_data: FrameCollection, context: ExecutionContext,
    ) -> ObjectDetectionData:
        output_path = self.__resolve_output_path(input_data, context)

        if self.__is_execution_cached(output_path, input_data.episode_id, context):
            context.logger.info(f'Skipping {input_data.episode_id} (cached object detection)')
            return self.__construct_object_data(input_data, output_path)

        context.logger.info(f'Detecting objects for {input_data.episode_id}')
        context.mark_step_started(self.name, input_data.episode_id)

        context.mark_step_completed(self.name, input_data.episode_id)
        return self.__construct_object_data(input_data, output_path)

    def __is_execution_cached(
        self, output_path: Path, episode_id: str, context: ExecutionContext,
    ) -> bool:
        if not output_path.exists():
            return False
        if context.force_rerun:
            return False
        return context.is_step_completed(self.name, episode_id)

    @staticmethod
    def __resolve_output_path(
        input_data: FrameCollection, context: ExecutionContext,
    ) -> Path:
        output_filename = f'{context.series_name}_{input_data.episode_info.episode_code()}_objects.json'
        return context.get_output_path(
            input_data.episode_info, 'object_detections', output_filename,
        )

    @staticmethod
    def __construct_object_data(
        input_data: FrameCollection, output_path: Path,
    ) -> ObjectDetectionData:
        return ObjectDetectionData(
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            path=output_path,
        )
