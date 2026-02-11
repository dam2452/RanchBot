from preprocessor.config.step_configs import SceneDetectionConfig
from preprocessor.core.artifacts import (
    SceneCollection,
    TranscodedVideo,
)
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.lib.io.files import (
    atomic_write_json,
    load_json,
)
from preprocessor.lib.media.scene_detection import TransNetWrapper


class SceneDetectorStep(PipelineStep[TranscodedVideo, SceneCollection, SceneDetectionConfig]):

    def __init__(self, config: SceneDetectionConfig):
        super().__init__(config)
        self.transnet = TransNetWrapper()
        self._model_loaded = False

    @property
    def name(self) -> str:
        return 'scene_detection'

    def execute(self, input_data: TranscodedVideo, context: ExecutionContext) -> SceneCollection:
        output_filename = f'{context.series_name}_{input_data.episode_info.episode_code()}_scenes.json'
        output_path = context.get_output_path(input_data.episode_info, 'scene_timestamps', output_filename)
        if output_path.exists() and (not context.force_rerun):
            if context.is_step_completed(self.name, input_data.episode_id):
                context.logger.info(f'Skipping {input_data.episode_id} (cached)')
                scenes_data = load_json(output_path)
                return SceneCollection(
                    path=output_path,
                    video_path=input_data.path,
                    episode_id=input_data.episode_id,
                    episode_info=input_data.episode_info,
                    scenes=scenes_data.get('scenes', []),
                    threshold=self.config.threshold,
                    min_scene_len=self.config.min_scene_len,
                )
        if not self._model_loaded:
            context.logger.info('Loading TransNetV2 model...')
            self.transnet.load_model()
            self._model_loaded = True
        context.logger.info(f'Detecting scenes in {input_data.episode_id}')
        context.mark_step_started(self.name, input_data.episode_id)
        scenes = self.transnet.detect_scenes(
            input_data.path,
            threshold=self.config.threshold,
            min_scene_len=self.config.min_scene_len,
        )
        video_info = self.transnet.__get_video_info(input_data.path)
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
        atomic_write_json(output_path, output_data)
        context.mark_step_completed(self.name, input_data.episode_id)
        return SceneCollection(
            path=output_path,
            video_path=input_data.path,
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            scenes=scenes,
            threshold=self.config.threshold,
            min_scene_len=self.config.min_scene_len,
        )

    def cleanup(self) -> None:
        if self._model_loaded:
            self.transnet.cleanup()
            self._model_loaded = False
