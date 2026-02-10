from datetime import datetime
import json
from pathlib import Path
import shutil
import subprocess
from typing import (
    Any,
    Dict,
    List,
)

from PIL import Image
import decord

from preprocessor.config.step_configs import FrameExportConfig
from preprocessor.config.types import FrameRequest
from preprocessor.core.artifacts import (
    FrameCollection,
    SceneCollection,
)
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.lib.io.files import atomic_write_json
from preprocessor.modules.video.strategies.strategy_factory import KeyframeStrategyFactory


class FrameExporterStep(PipelineStep[SceneCollection, FrameCollection, FrameExportConfig]):

    def __init__(self, config: FrameExportConfig):
        super().__init__(config)
        decord.bridge.set_bridge('native')
        self.strategy = KeyframeStrategyFactory.create(self.config.keyframe_strategy, self.config.frames_per_scene)

    @property
    def name(self) -> str:
        return 'frame_export'

    def execute(self, input_data: SceneCollection, context: ExecutionContext) -> FrameCollection:
        episode_dir = context.get_output_path(input_data.episode_info, 'exported_frames', '')
        metadata_filename = f'{context.series_name}_{input_data.episode_info.episode_code()}_frame_metadata.json'
        metadata_file = episode_dir / metadata_filename
        if metadata_file.exists() and (not context.force_rerun):
            if context.is_step_completed(self.name, input_data.episode_id):
                context.logger.info(f'Skipping {input_data.episode_id} (cached)')
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                return FrameCollection(
                    episode_id=input_data.episode_id,
                    episode_info=input_data.episode_info,
                    directory=episode_dir,
                    frame_count=metadata['statistics']['total_frames'],
                    metadata_path=metadata_file,
                )
        if episode_dir.exists():
            context.logger.info(f'Cleaning incomplete frames from previous run: {episode_dir}')
            shutil.rmtree(episode_dir, ignore_errors=True)
        episode_dir.mkdir(parents=True, exist_ok=True)
        video_path = input_data.video_path
        if not video_path.exists():
            raise FileNotFoundError(f'Video file not found for frame export: {video_path}')
        data = {'scene_timestamps': {'scenes': input_data.scenes}}
        frame_requests = self.strategy.extract_frame_requests(video_path, data)
        if not frame_requests:
            context.logger.warning(f'No frames to extract for {input_data.episode_id}')
            return FrameCollection(
                episode_id=input_data.episode_id,
                episode_info=input_data.episode_info,
                directory=episode_dir,
                frame_count=0,
                metadata_path=metadata_file,
            )
        context.logger.info(f'Extracting {len(frame_requests)} keyframes from {video_path.name}')
        context.mark_step_started(self.name, input_data.episode_id)
        try:
            self._extract_frames(video_path, frame_requests, episode_dir, input_data.episode_info, context)
            self._write_metadata(frame_requests, input_data.episode_info, video_path, context, metadata_file)
        except Exception as e:
            context.logger.error(f'Failed to extract frames from {video_path}: {e}')
            shutil.rmtree(episode_dir, ignore_errors=True)
            raise
        context.mark_step_completed(self.name, input_data.episode_id)
        return FrameCollection(
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            directory=episode_dir,
            frame_count=len(frame_requests),
            metadata_path=metadata_file,
        )

    def _extract_frames(
        self,
        video_file: Path,
        frame_requests: List[FrameRequest],
        episode_dir: Path,
        episode_info,
        context: ExecutionContext,
    ) -> None:
        video_metadata = self._get_video_metadata(video_file)
        dar = self._calculate_display_aspect_ratio(video_metadata)
        vr = decord.VideoReader(str(video_file), ctx=decord.cpu(0))
        for req in frame_requests:
            frame_num = req['frame_number']
            self._extract_and_save_frame(vr, frame_num, episode_dir, episode_info, dar, context.series_name)
        del vr

    def _extract_and_save_frame(
        self,
        vr,
        frame_num: int,
        episode_dir: Path,
        episode_info,
        dar: float,
        series_name: str,
    ) -> None:
        frame_np = vr[frame_num].asnumpy()
        frame_pil = Image.fromarray(frame_np)
        resized = self._resize_frame(frame_pil, dar)
        base_filename = f'{series_name}_{episode_info.episode_code()}'
        filename = f'{base_filename}_frame_{frame_num:06d}.jpg'
        resized.save(episode_dir / filename, quality=90)

    @staticmethod
    def _get_video_metadata(video_path: Path) -> Dict[str, Any]:
        cmd = [
            'ffprobe', '-v', 'error', '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height,sample_aspect_ratio,display_aspect_ratio',
            '-of', 'json', str(video_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        probe_data: Dict[str, Any] = json.loads(result.stdout)
        streams: List[Dict[str, Any]] = probe_data.get('streams', [])
        if not streams:
            raise ValueError(f'No video streams found in {video_path}')
        return streams[0]

    @staticmethod
    def _calculate_display_aspect_ratio(metadata: Dict[str, Any]) -> float:
        width = metadata.get('width', 0)
        height = metadata.get('height', 0)
        if width == 0 or height == 0:
            raise ValueError('Invalid video dimensions')
        sar_str = metadata.get('sample_aspect_ratio', '1:1')
        if sar_str == 'N/A' or not sar_str:
            sar_str = '1:1'
        try:
            sar_num, sar_denom = [int(x) for x in sar_str.split(':')]
            sar = sar_num / sar_denom if sar_denom != 0 else 1.0
        except (ValueError, ZeroDivisionError):
            sar = 1.0
        return width / height * sar

    def _resize_frame(self, frame: Image.Image, display_aspect_ratio: float) -> Image.Image:
        target_width = self.config.resolution.width
        target_height = self.config.resolution.height
        target_aspect = target_width / target_height
        if abs(display_aspect_ratio - target_aspect) < 0.01:
            return frame.resize((target_width, target_height), Image.Resampling.LANCZOS)
        if display_aspect_ratio > target_aspect:
            new_height = target_height
            new_width = int(target_height * display_aspect_ratio)
            resized = frame.resize((new_width, new_height), Image.Resampling.LANCZOS)
            x_crop = (new_width - target_width) // 2
            cropped = resized.crop((x_crop, 0, x_crop + target_width, target_height))
            return cropped
        new_width = target_width
        new_height = int(target_width / display_aspect_ratio)
        resized = frame.resize((new_width, new_height), Image.Resampling.LANCZOS)
        result = Image.new('RGB', (target_width, target_height), (0, 0, 0))
        y_offset = (target_height - new_height) // 2
        result.paste(resized, (0, y_offset))
        return result

    def _write_metadata(
        self,
        frame_requests: List[FrameRequest],
        episode_info,
        source_video: Path,
        context: ExecutionContext,
        metadata_file: Path,
    ) -> None:
        frame_types_count = {}
        frames_with_paths = []
        base_filename = f'{context.series_name}_{episode_info.episode_code()}'
        for frame in frame_requests:
            frame_type = frame.get('type', 'unknown')
            frame_types_count[frame_type] = frame_types_count.get(frame_type, 0) + 1
            frame_with_path = frame.copy()
            frame_num = frame['frame_number']
            frame_with_path['frame_path'] = f'{base_filename}_frame_{frame_num:06d}.jpg'
            frames_with_paths.append(frame_with_path)
        scene_numbers = {
            f.get('scene_number', -1)
            for f in frame_requests
            if f.get('scene_number', -1) != -1
        }
        metadata = {
            'generated_at': datetime.now().isoformat(),
            'episode_info': {
                'season': episode_info.season,
                'episode_number': episode_info.relative_episode,
                'absolute_episode': episode_info.absolute_episode,
            },
            'source_video': str(source_video),
            'processing_parameters': {
                'frame_width': self.config.resolution.width,
                'frame_height': self.config.resolution.height,
                'keyframe_strategy': self.config.keyframe_strategy.value,
                'frames_per_scene': self.config.frames_per_scene,
            },
            'statistics': {
                'total_frames': len(frame_requests),
                'frame_types': frame_types_count,
                'total_scenes': len(scene_numbers),
                'timestamp_range': {
                    'start': min((f.get('timestamp', 0) for f in frame_requests), default=0),
                    'end': max((f.get('timestamp', 0) for f in frame_requests), default=0),
                },
            },
            'frames': frames_with_paths,
        }
        atomic_write_json(metadata_file, metadata, indent=2)
