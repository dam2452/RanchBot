from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
)

from preprocessor.config.step_configs import SceneDetectionConfig
from preprocessor.core.artifacts import (
    SceneCollection,
    TranscodedVideo,
)
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.core.output_descriptors import (
    JsonFileOutput,
    OutputDescriptor,
)
from preprocessor.services.io.files import FileOperations
from preprocessor.services.media.scene_detection import TransNetWrapper


class SceneDetectorStep(PipelineStep[TranscodedVideo, SceneCollection, SceneDetectionConfig]):
    def __init__(self, config: SceneDetectionConfig) -> None:
        super().__init__(config)
        self.__transnet = TransNetWrapper()
        self.__model_loaded = False

    @property
    def name(self) -> str:
        return 'scene_detection'

    @property
    def supports_batch_processing(self) -> bool:
        return True

    def get_output_descriptors(self) -> List[OutputDescriptor]:
        return [
            JsonFileOutput(
                pattern="{season}/{episode}.json",
                subdir="scene_detections",
                min_size_bytes=10,
            ),
        ]

    def setup_resources(self, context: ExecutionContext) -> None:
        if not self.__model_loaded:
            context.logger.info('Loading TransNetV2 model...')
            self.__transnet.load_model()
            self.__model_loaded = True

    def execute_batch(
        self, input_data: List[TranscodedVideo], context: ExecutionContext,
    ) -> List[SceneCollection]:
        return self._execute_with_threadpool(
            input_data, context, self.config.max_parallel_episodes, self.__execute_single,
        )

    def teardown_resources(self, context: ExecutionContext) -> None:
        if self.__model_loaded:
            self.__transnet.cleanup()
            self.__model_loaded = False
            context.logger.info('TransNetV2 model unloaded')

    def cleanup(self) -> None:
        if self.__model_loaded:
            self.__transnet.cleanup()
            self.__model_loaded = False

    def execute(
            self, input_data: TranscodedVideo, context: ExecutionContext,
    ) -> SceneCollection:
        output_path = self.__resolve_output_path(input_data, context)

        if self._check_cache_validity(output_path, context, input_data.episode_id, 'cached'):
            return self.__load_cached_result(output_path, input_data)

        self.__prepare_detection_environment(context)

        context.logger.info(f'Detecting scenes in {input_data.episode_id}')
        context.mark_step_started(self.name, input_data.episode_id)

        scenes = self.__detect_scenes(input_data.path)
        self.__save_detection_results(scenes, input_data.path, output_path)

        context.mark_step_completed(self.name, input_data.episode_id)
        return self.__construct_scene_collection(output_path, input_data, scenes)

    def __execute_single(
        self, input_data: TranscodedVideo, context: ExecutionContext,
    ) -> SceneCollection:
        output_path = self.__resolve_output_path(input_data, context)

        if self._check_cache_validity(output_path, context, input_data.episode_id, 'cached'):
            return self.__load_cached_result(output_path, input_data)

        context.logger.info(f'Detecting scenes in {input_data.episode_id}')
        context.mark_step_started(self.name, input_data.episode_id)

        scenes = self.__detect_scenes(input_data.path)
        self.__save_detection_results(scenes, input_data.path, output_path)

        context.mark_step_completed(self.name, input_data.episode_id)
        return self.__construct_scene_collection(output_path, input_data, scenes)

    def __prepare_detection_environment(self, context: ExecutionContext) -> None:
        if not self.__model_loaded:
            context.logger.info('Loading TransNetV2 model...')
            self.__transnet.load_model()
            self.__model_loaded = True

    def __detect_scenes(self, video_path: Path) -> List[Dict[str, Any]]:
        return self.__transnet.detect_scenes(
            video_path,
            threshold=self.config.threshold,
            min_scene_len=self.config.min_scene_len,
        )

    def __save_detection_results(
            self,
            scenes: List[Dict[str, Any]],
            video_path: Path,
            output_path: Path,
    ) -> None:
        video_info = self.__transnet.get_video_info(video_path)
        output_data = self.__build_results_payload(scenes, video_info)
        FileOperations.atomic_write_json(output_path, output_data)

    def __build_results_payload(
            self,
            scenes: List[Dict[str, Any]],
            video_info: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            'total_scenes': len(scenes),
            'video_info': video_info,
            'detection_settings': {
                'threshold': self.config.threshold,
                'min_scene_len': self.config.min_scene_len,
                'method': 'transnetv2',
            },
            'scenes': scenes,
        }

    def __load_cached_result(
            self,
            output_path: Path,
            input_data: TranscodedVideo,
    ) -> SceneCollection:
        scenes_data = FileOperations.load_json(output_path)
        return SceneCollection(
            path=output_path,
            video_path=input_data.path,
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            scenes=scenes_data.get('scenes', []),
            threshold=self.config.threshold,
            min_scene_len=self.config.min_scene_len,
        )

    def __construct_scene_collection(
            self,
            output_path: Path,
            input_data: TranscodedVideo,
            scenes: List[Dict[str, Any]],
    ) -> SceneCollection:
        return SceneCollection(
            path=output_path,
            video_path=input_data.path,
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            scenes=scenes,
            threshold=self.config.threshold,
            min_scene_len=self.config.min_scene_len,
        )

    def __resolve_output_path(
            self,
            input_data: TranscodedVideo,
            context: ExecutionContext,
    ) -> Path:
        return self._resolve_output_path(
            0,
            context,
            {
                'season': input_data.episode_info.season_code(),
                'episode': input_data.episode_info.episode_code(),
            },
        )
