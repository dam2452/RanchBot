from pathlib import Path
from typing import List

from preprocessor.config.step_configs import ObjectDetectionConfig
from preprocessor.core.artifacts import (
    FrameCollection,
    ObjectDetectionData,
)
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext


class ObjectDetectionStep(PipelineStep[FrameCollection, ObjectDetectionData, ObjectDetectionConfig]):
    def __init__(self, config: ObjectDetectionConfig) -> None:
        super().__init__(config)
        self.__model = None

    @property
    def name(self) -> str:
        return 'object_detection'

    def cleanup(self) -> None:
        self.__model = None

    @property
    def supports_batch_processing(self) -> bool:
        return True

    def setup_resources(self, context: ExecutionContext) -> None:
        if self.__model is None:
            context.logger.info('Loading Object Detection model...')

    def execute_batch(
        self, input_data: List[FrameCollection], context: ExecutionContext,
    ) -> List[ObjectDetectionData]:
        return self._execute_with_threadpool(
            input_data, context, self.config.max_parallel_episodes, self.__execute_single,
        )

    def teardown_resources(self, context: ExecutionContext) -> None:
        if self.__model:
            context.logger.info('Object Detection model unloaded')
            self.__model = None

    def __execute_single(
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
