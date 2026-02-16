# pylint: disable=duplicate-code
from pathlib import Path
from typing import (
    Dict,
    List,
)

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


class ObjectDetectionStep(
    PipelineStep[FrameCollection, ObjectDetectionData, ObjectDetectionConfig],
):
    def __init__(self, config: ObjectDetectionConfig) -> None:
        super().__init__(config)
        self.__model = None

    @property
    def supports_batch_processing(self) -> bool:
        return True

    def setup_resources(self, context: ExecutionContext) -> None:
        if self.__model is None:
            self.__load_model(context)

    def teardown_resources(self, context: ExecutionContext) -> None:
        if self.__model:
            self.__unload_model(context)

    def cleanup(self) -> None:
        self.__model = None

    def execute_batch(
        self, input_data: List[FrameCollection], context: ExecutionContext,
    ) -> List[ObjectDetectionData]:
        return self._execute_with_threadpool(
            input_data, context, self.config.max_parallel_episodes, self.execute,
        )

    def _process(
        self, input_data: FrameCollection, context: ExecutionContext,
    ) -> ObjectDetectionData:
        output_path = self._get_cache_path(input_data, context)
        # Main processing logic would go here
        return self.__construct_object_data(input_data, output_path)

    def get_output_descriptors(self) -> List[OutputDescriptor]:
        return [
            JsonFileOutput(
                subdir="detections/objects",
                pattern="{season}/{episode}.json",
                min_size_bytes=10,
            ),
        ]

    def _get_cache_path(
        self, input_data: FrameCollection, context: ExecutionContext,
    ) -> Path:
        return self._resolve_output_path(
            0,
            context,
            self.__create_path_variables(input_data),
        )

    def _load_from_cache(
        self, cache_path: Path, input_data: FrameCollection, context: ExecutionContext,
    ) -> ObjectDetectionData:
        return self.__construct_object_data(input_data, cache_path)

    @staticmethod
    def __load_model(context: ExecutionContext) -> None:
        context.logger.info('Loading Object Detection model...')
        # Model loading logic implementation

    def __unload_model(self, context: ExecutionContext) -> None:
        context.logger.info('Object Detection model unloaded')
        self.__model = None

    @staticmethod
    def __create_path_variables(input_data: FrameCollection) -> Dict[str, str]:
        return {
            'season': f'S{input_data.episode_info.season:02d}',
            'episode': input_data.episode_info.episode_code(),
        }

    @staticmethod
    def __construct_object_data(
        input_data: FrameCollection, output_path: Path,
    ) -> ObjectDetectionData:
        return ObjectDetectionData(
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            path=output_path,
        )
