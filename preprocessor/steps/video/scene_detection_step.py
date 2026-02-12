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
from preprocessor.services.io.files import FileOperations
from preprocessor.services.media.scene_detection import TransNetWrapper


class SceneDetectorStep(PipelineStep[TranscodedVideo, SceneCollection, SceneDetectionConfig]):

    def __init__(self, config: SceneDetectionConfig) -> None:
        super().__init__(config)
        self.transnet = TransNetWrapper()
        self._model_loaded = False

    def cleanup(self) -> None:
        if self._model_loaded:
            self.transnet.cleanup()
            self._model_loaded = False

    def execute(self, input_data: TranscodedVideo, context: ExecutionContext) -> SceneCollection:
        output_path = self._get_output_path(input_data, context)

        if self._check_cache_validity(output_path, context, input_data.episode_id, 'cached'):
            return self._load_cached_result(output_path, input_data)

        self._ensure_model_loaded(context)
        context.logger.info(f'Detecting scenes in {input_data.episode_id}')
        context.mark_step_started(self.name, input_data.episode_id)

        scenes = self._detect_scenes(input_data.path)
        self._save_results(scenes, input_data.path, output_path)

        context.mark_step_completed(self.name, input_data.episode_id)
        return self._create_scene_collection(output_path, input_data, scenes)

    @property
    def name(self) -> str:
        return 'scene_detection'

    @staticmethod
    def _get_output_path(input_data: TranscodedVideo, context: ExecutionContext) -> Path:
        output_filename = f'{context.series_name}_{input_data.episode_info.episode_code()}_scenes.json'
        return context.get_output_path(input_data.episode_info, 'scene_timestamps', output_filename)

    def _load_cached_result(self, output_path: Path, input_data: TranscodedVideo) -> SceneCollection:
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

    def _ensure_model_loaded(self, context: ExecutionContext) -> None:
        if not self._model_loaded:
            context.logger.info('Loading TransNetV2 model...')
            self.transnet.load_model()
            self._model_loaded = True

    def _detect_scenes(self, video_path: Path) -> List[Dict[str, Any]]:
        return self.transnet.detect_scenes(
            video_path,
            threshold=self.config.threshold,
            min_scene_len=self.config.min_scene_len,
        )

    def _save_results(self, scenes: List[Dict[str, Any]], video_path: Path, output_path: Path) -> None:
        video_info = self.transnet._TransNetWrapper__get_video_info(video_path)
        output_data = {
            'total_scenes': len(scenes),
            'video_info': video_info,
            'detection_settings': {
                'threshold': self.config.threshold,
                'min_scene_len': self.config.min_scene_len,
                'method': 'transnetv2',
            },
            'scenes': scenes,
        }
        FileOperations.atomic_write_json(output_path, output_data)

    def _create_scene_collection(
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
