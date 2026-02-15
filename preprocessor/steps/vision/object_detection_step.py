from pathlib import Path
from typing import List

from preprocessor.config.step_configs import ObjectDetectionConfig
from preprocessor.core.artifacts import (
    FrameCollection,
    ObjectDetectionData,
)
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.core.output_descriptors import (
    JsonFileOutput,
    OutputDescriptor,
)


class ObjectDetectionStep(PipelineStep[FrameCollection, ObjectDetectionData, ObjectDetectionConfig]):
    def get_output_descriptors(self) -> List[OutputDescriptor]:
        """Define output file descriptors for object detection step."""
        return [
            JsonFileOutput(
                subdir="detections/objects",
                pattern="{season}/{episode}.json",
                min_size_bytes=10,
            ),
        ]


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

        if self._check_cache_validity(output_path, context, input_data.episode_id, 'cached object detection'):
            return self.__construct_object_data(input_data, output_path)

        context.logger.info(f'Detecting objects for {input_data.episode_id}')
        context.mark_step_started(self.name, input_data.episode_id)

        context.mark_step_completed(self.name, input_data.episode_id)
        return self.__construct_object_data(input_data, output_path)

    def execute(
        self, input_data: FrameCollection, context: ExecutionContext,
    ) -> ObjectDetectionData:
        output_path = self.__resolve_output_path(input_data, context)

        if self._check_cache_validity(output_path, context, input_data.episode_id, 'cached object detection'):
            return self.__construct_object_data(input_data, output_path)

        context.logger.info(f'Detecting objects for {input_data.episode_id}')
        context.mark_step_started(self.name, input_data.episode_id)

        context.mark_step_completed(self.name, input_data.episode_id)
        return self.__construct_object_data(input_data, output_path)

    def __resolve_output_path(
        self, input_data: FrameCollection, context: ExecutionContext,
    ) -> Path:
        return self._resolve_output_path(
            0,
            context,
            {
                'season': f'S{input_data.episode_info.season:02d}',
                'episode': input_data.episode_info.episode_code(),
            },
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
