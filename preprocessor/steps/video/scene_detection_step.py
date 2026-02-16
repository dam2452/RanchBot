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

    def setup_resources(self, context: ExecutionContext) -> None:
        if not self.__model_loaded:
            context.logger.info('Loading TransNetV2 model...')
            self.__transnet.load_model()
            self.__model_loaded = True

    def teardown_resources(self, context: ExecutionContext) -> None:
        if self.__model_loaded:
            self.__transnet.cleanup()
            self.__model_loaded = False
            context.logger.info('TransNetV2 model unloaded')

    def cleanup(self) -> None:
        if self.__model_loaded:
            self.__transnet.cleanup()
            self.__model_loaded = False

    def execute_batch(
        self, input_data: List[TranscodedVideo], context: ExecutionContext,
    ) -> List[SceneCollection]:
        return self._execute_with_threadpool(
            input_data, context, self.config.max_parallel_episodes, self.execute,
        )

    def _process(
        self, input_data: TranscodedVideo, context: ExecutionContext,
    ) -> SceneCollection:
        output_path = self._get_cache_path(input_data, context)

        self.__prepare_detection_environment(context)
        scenes = self.__detect_scenes(input_data.path)

        # Retrieve video info needed for the output payload
        video_info = self.__transnet.get_video_info(input_data.path)
        self.__save_detection_results(scenes, video_info, output_path)

        return self.__construct_scene_collection(output_path, input_data, scenes)

    def get_output_descriptors(self) -> List[OutputDescriptor]:
        return [
            JsonFileOutput(
                pattern="{season}/{episode}.json",
                subdir="scene_detections",
                min_size_bytes=10,
            ),
        ]

    def _get_cache_path(
        self, input_data: TranscodedVideo, context: ExecutionContext,
    ) -> Path:
        return self._get_standard_cache_path(input_data, context)

    def _load_from_cache(
        self, cache_path: Path, input_data: TranscodedVideo, context: ExecutionContext,
    ) -> SceneCollection:
        scenes_data: Dict[str, Any] = FileOperations.load_json(cache_path)
        return self.__construct_scene_collection(
            cache_path, input_data, scenes_data.get('scenes', []),
        )

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
        video_info: Dict[str, Any],
        output_path: Path,
    ) -> None:
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

    def __construct_scene_collection(
        self,
        output_path: Path,
        input_data: TranscodedVideo,
        scenes: List[Dict[str, Any]],
    ) -> SceneCollection:
        return SceneCollection(
            path=output_path,
            video_path=input_data.path,
            source_video_path=getattr(input_data, 'source_video_path', input_data.path),
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            scenes=scenes,
            threshold=self.config.threshold,
            min_scene_len=self.config.min_scene_len,
        )
