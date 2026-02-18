import bisect
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import json
from pathlib import Path
import shutil
from typing import (
    Any,
    Dict,
    List,
)

from PIL import Image

from preprocessor.config.step_configs import FrameExportConfig
from preprocessor.config.types import FrameRequest
from preprocessor.core.artifacts import (
    FrameCollection,
    SceneCollection,
)
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.core.output_descriptors import (
    DirectoryOutput,
    create_frames_output,
)
from preprocessor.core.temp_files import StepTempFile
from preprocessor.services.io.files import FileOperations
from preprocessor.services.media.ffmpeg import FFmpegWrapper
from preprocessor.services.video.strategies.strategy_factory import KeyframeStrategyFactory


class FrameExporterStep(PipelineStep[SceneCollection, FrameCollection, FrameExportConfig]):
    def __init__(self, config: FrameExportConfig) -> None:
        super().__init__(config)
        self.__strategy = KeyframeStrategyFactory.create(
            self.config.keyframe_strategy,
            self.config.frames_per_scene,
            self.config.scene_change_offset_seconds,
        )

    @property
    def supports_batch_processing(self) -> bool:
        return True

    def execute_batch(
        self, input_data: List[SceneCollection], context: ExecutionContext,
    ) -> List[FrameCollection]:
        return self._execute_with_threadpool(
            input_data, context, self.config.max_parallel_episodes, self.execute,
        )

    def _process(
        self, input_data: SceneCollection, context: ExecutionContext,
    ) -> FrameCollection:
        metadata_file = self._get_cache_path(input_data, context)
        episode_dir = metadata_file.parent

        self.__prepare_episode_directory(episode_dir, context)
        frame_requests = self.__extract_frame_requests(input_data)

        if not frame_requests:
            return self.__construct_empty_result(
                episode_dir, metadata_file, input_data, context,
            )

        context.logger.info(
            f'Extracting {len(frame_requests)} keyframes from {input_data.video_path.name}',
        )

        self.__process_frame_extraction(
            input_data.video_path,
            frame_requests,
            episode_dir,
            input_data,
            metadata_file,
            context,
        )

        return FrameCollection(
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            directory=episode_dir,
            frame_count=len(frame_requests),
            metadata_path=metadata_file,
        )

    def get_output_descriptors(self) -> List[DirectoryOutput]:
        return [create_frames_output()]

    def _get_cache_path(
        self, input_data: SceneCollection, context: ExecutionContext,
    ) -> Path:
        episode_dir = self._get_standard_cache_path(input_data, context)
        metadata_filename = (
            f'{context.series_name}_'
            f'{input_data.episode_info.episode_code()}_frame_metadata.json'
        )
        return episode_dir / metadata_filename

    def _load_from_cache(
        self, cache_path: Path, input_data: SceneCollection, context: ExecutionContext,
    ) -> FrameCollection:
        episode_dir = cache_path.parent
        with open(cache_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        return FrameCollection(
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            directory=episode_dir,
            frame_count=metadata['statistics']['total_frames'],
            metadata_path=cache_path,
        )

    def __extract_frame_requests(
        self, input_data: SceneCollection,
    ) -> List[FrameRequest]:
        video_path = input_data.video_path
        if not video_path.exists():
            raise FileNotFoundError(f'Video file not found for frame export: {video_path}')
        data = {
            'scene_timestamps': {'scenes': input_data.scenes},
        }
        return self.__strategy.extract_frame_requests(video_path, data)

    def __process_frame_extraction(
        self,
        video_path: Path,
        frame_requests: List[FrameRequest],
        episode_dir: Path,
        input_data: SceneCollection,
        metadata_file: Path,
        context: ExecutionContext,
    ) -> None:
        try:
            self.__extract_frames(
                video_path,
                frame_requests,
                episode_dir,
                input_data.episode_info,
                context,
            )
            self.__write_metadata(
                frame_requests,
                input_data.episode_info,
                video_path,
                context,
                metadata_file,
            )
        except (Exception, KeyboardInterrupt) as e:
            error_type = "interrupted" if isinstance(e, KeyboardInterrupt) else "failed"
            context.logger.error(f'Frame extraction {error_type} for {video_path}: {e}')
            shutil.rmtree(episode_dir, ignore_errors=True)
            raise

    def __extract_frames(
        self,
        video_file: Path,
        frame_requests: List[FrameRequest],
        episode_dir: Path,
        episode_info,
        context: ExecutionContext,
    ) -> None:
        video_metadata = self.__fetch_video_metadata(video_file)
        dar = self.__calculate_display_aspect_ratio(video_metadata)

        context.logger.info(f'Finding I-frames (keyframes) in {video_file.name}')
        keyframes = self.__get_all_keyframes(video_file)
        context.logger.info(f'Found {len(keyframes)} I-frames')

        for req in frame_requests:
            target_timestamp = req['timestamp']
            snapped_timestamp = self.__snap_to_keyframe(keyframes, target_timestamp)

            if abs(snapped_timestamp - target_timestamp) > 0.1:
                context.logger.debug(
                    f'Snapped {target_timestamp:.3f}s -> {snapped_timestamp:.3f}s '
                    f'(I-frame, delta: {snapped_timestamp - target_timestamp:.3f}s)',
                )

            req['timestamp'] = snapped_timestamp
            req['original_timestamp'] = target_timestamp
            req['snapped_to_keyframe'] = True

        seen_ms: set[int] = set()
        unique_timestamps: List[float] = []
        for req in frame_requests:
            ts_ms = int(req['timestamp'] * 1000)
            if ts_ms not in seen_ms:
                seen_ms.add(ts_ms)
                unique_timestamps.append(req['timestamp'])

        with ThreadPoolExecutor(max_workers=self.config.max_parallel_frames) as executor:
            futures = [
                executor.submit(
                    self.__extract_and_save_frame,
                    video_file,
                    timestamp,
                    episode_dir,
                    episode_info,
                    dar,
                    context.series_name,
                )
                for timestamp in unique_timestamps
            ]
            for future in futures:
                future.result()

    def __extract_and_save_frame(
        self,
        video_file: Path,
        timestamp: float,
        episode_dir: Path,
        episode_info,
        dar: float,
        series_name: str,
    ) -> None:
        frame_pil = self.__extract_frame_at_timestamp(video_file, timestamp)
        resized = self.__resize_frame(frame_pil, dar)

        base_filename = f'{series_name}_{episode_info.episode_code()}'
        timestamp_ms = int(timestamp * 1000)
        filename = f'{base_filename}_frame_{timestamp_ms:08d}.jpg'
        final_path = episode_dir / filename

        with StepTempFile(final_path) as temp_path:
            resized.save(temp_path, format='JPEG', quality=90)

    @staticmethod
    def __extract_frame_at_timestamp(video_file: Path, timestamp: float) -> Image.Image:
        return FFmpegWrapper.extract_frame_at_timestamp(video_file, timestamp)

    def __resize_frame(
        self, frame: Image.Image, display_aspect_ratio: float,
    ) -> Image.Image:
        target_width = self.config.resolution.width
        target_height = self.config.resolution.height
        target_aspect = target_width / target_height

        if abs(display_aspect_ratio - target_aspect) < 0.01:
            return frame.resize(
                (target_width, target_height), Image.Resampling.LANCZOS,
            )

        if display_aspect_ratio > target_aspect:
            new_width = target_width
            new_height = int(target_width / display_aspect_ratio)
            resized = frame.resize((new_width, new_height), Image.Resampling.LANCZOS)
            result = Image.new('RGB', (target_width, target_height), (0, 0, 0))
            y_offset = (target_height - new_height) // 2
            result.paste(resized, (0, y_offset))
            return result

        new_height = target_height
        new_width = int(target_height * display_aspect_ratio)
        resized = frame.resize((new_width, new_height), Image.Resampling.LANCZOS)
        result = Image.new('RGB', (target_width, target_height), (0, 0, 0))
        x_offset = (target_width - new_width) // 2
        result.paste(resized, (x_offset, 0))
        return result

    def __write_metadata(
        self,
        frame_requests: List[FrameRequest],
        episode_info,
        source_video: Path,
        context: ExecutionContext,
        metadata_file: Path,
    ) -> None:
        frame_types_count: Dict[str, int] = {}
        frames_with_paths: List[Dict[str, Any]] = []
        base_filename = f'{context.series_name}_{episode_info.episode_code()}'

        for frame in frame_requests:
            frame_type = frame.get('type', 'unknown')
            frame_types_count[frame_type] = frame_types_count.get(frame_type, 0) + 1

            frame_with_path = frame.copy()
            timestamp_ms = int(frame['timestamp'] * 1000)
            frame_with_path['frame_path'] = f'{base_filename}_frame_{timestamp_ms:08d}.jpg'
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
                    'start': min(
                        (f.get('timestamp', 0) for f in frame_requests), default=0,
                    ),
                    'end': max(
                        (f.get('timestamp', 0) for f in frame_requests), default=0,
                    ),
                },
            },
            'frames': frames_with_paths,
        }
        FileOperations.atomic_write_json(metadata_file, metadata, indent=2)

    @staticmethod
    def __prepare_episode_directory(
        episode_dir: Path, context: ExecutionContext,
    ) -> None:
        if episode_dir.exists():
            context.logger.info(
                f'Cleaning incomplete frames from previous run: {episode_dir}',
            )
            shutil.rmtree(episode_dir, ignore_errors=True)
        episode_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def __construct_empty_result(
        episode_dir: Path,
        metadata_file: Path,
        input_data: SceneCollection,
        context: ExecutionContext,
    ) -> FrameCollection:
        context.logger.warning(f'No frames to extract for {input_data.episode_id}')
        return FrameCollection(
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            directory=episode_dir,
            frame_count=0,
            metadata_path=metadata_file,
        )

    @staticmethod
    def __fetch_video_metadata(video_path: Path) -> Dict[str, Any]:
        probe_data = FFmpegWrapper.probe_video(video_path)
        streams: List[Dict[str, Any]] = probe_data.get('streams', [])

        video_streams = [s for s in streams if s.get('codec_type') == 'video']
        if not video_streams:
            raise ValueError(f'No video streams found in {video_path}')
        return video_streams[0]

    @staticmethod
    def __calculate_display_aspect_ratio(metadata: Dict[str, Any]) -> float:
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

    @staticmethod
    def __get_all_keyframes(video_file: Path) -> List[float]:
        return sorted(FFmpegWrapper.get_keyframe_timestamps(video_file))

    @staticmethod
    def __snap_to_keyframe(
        keyframes: List[float],
        target_timestamp: float,
    ) -> float:
        if not keyframes:
            return target_timestamp

        idx = bisect.bisect_left(keyframes, target_timestamp)

        if idx < len(keyframes):
            return keyframes[idx]

        return keyframes[-1]
