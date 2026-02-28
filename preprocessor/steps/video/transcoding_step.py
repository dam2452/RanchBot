from dataclasses import replace
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
)

from preprocessor.config.step_configs import TranscodeConfig
from preprocessor.core.artifacts import (
    SourceVideo,
    TranscodedVideo,
)
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.core.output_descriptors import FileOutput
from preprocessor.core.temp_files import StepTempFile
from preprocessor.services.media.ffmpeg import FFmpegWrapper
from preprocessor.services.media.transcode_params import TranscodeParams


class VideoTranscoderStep(PipelineStep[SourceVideo, TranscodedVideo, TranscodeConfig]):
    __CODEC_EFFICIENCY: Dict[str, float] = {
        'h264': 1.0, 'avc': 1.0,
        'hevc': 2.0, 'h265': 2.0,
        'vp9': 2.85, 'av1': 4.0,
    }
    __TARGET_FRAMERATE: float = 25.0
    __command_logged: bool = False

    @property
    def supports_batch_processing(self) -> bool:
        return True

    def execute_batch(
        self, input_data: List[SourceVideo], context: ExecutionContext,
    ) -> List[TranscodedVideo]:
        total = len(input_data)
        parallel = min(self.config.max_parallel_episodes, total)
        context.logger.info(
            f'Transcoding {total} videos (processing {parallel} in parallel)',
        )
        return self._execute_with_threadpool(
            input_data, context, self.config.max_parallel_episodes, self.execute,
        )

    def _process(self, input_data: SourceVideo, context: ExecutionContext) -> TranscodedVideo:
        output_path = self._get_cache_path(input_data, context)

        probe_data = FFmpegWrapper.probe_video(input_data.path)
        params = self.__create_transcode_params(input_data, output_path, probe_data, context)

        self.__log_transcode_details(context, input_data, params, probe_data)
        self.__execute_ffmpeg_process(context, params, input_data.episode_id)

        return self.__construct_result_artifact(output_path, input_data)

    def get_output_descriptors(self) -> List[FileOutput]:
        return [
            FileOutput(
                pattern="{season}/{series_name}_{episode}.mp4",
                subdir="transcoded_videos",
                min_size_bytes=1024 * 1024,
            ),
        ]

    def _get_cache_path(self, input_data: SourceVideo, context: ExecutionContext) -> Path:
        return self._resolve_output_path(
            0,
            context,
            {
                'season': input_data.episode_info.season_code(),
                'episode': input_data.episode_info.episode_code(),
                'series_name': context.series_name,
            },
        )

    def _load_from_cache(
        self, cache_path: Path, input_data: SourceVideo, context: ExecutionContext,
    ) -> TranscodedVideo:
        return self.__construct_result_artifact(cache_path, input_data)

    def __create_transcode_params(
        self,
        input_data: SourceVideo,
        output_path: Path,
        probe_data: Dict[str, Any],
        context: ExecutionContext,
    ) -> TranscodeParams:
        target_fps = self.__TARGET_FRAMERATE
        bitrates = self.__compute_all_bitrate_settings(probe_data, context)
        is_upscaling = self.__is_upscaling(probe_data)

        return TranscodeParams(
            input_path=input_data.path,
            output_path=output_path,
            codec=self.config.codec,
            preset=self.config.preset,
            resolution=f'{self.config.resolution.width}:{self.config.resolution.height}',
            video_bitrate=f'{bitrates["video"]}M',
            minrate=f'{bitrates["min"]}M',
            maxrate=f'{bitrates["max"]}M',
            bufsize=f'{bitrates["buf"]}M',
            audio_bitrate=f'{self.__compute_audio_bitrate(probe_data, context)}k',
            gop_size=int(target_fps * self.config.keyframe_interval_seconds),
            target_fps=target_fps,
            deinterlace=self.__resolve_deinterlacing_strategy(input_data, context, probe_data),
            is_upscaling=is_upscaling,
            log_command=self.__should_log_command(),
        )

    def __is_upscaling(self, probe_data: Dict[str, Any]) -> bool:
        w, h = FFmpegWrapper.get_resolution(probe_data)
        sar_num, sar_denom = FFmpegWrapper.get_sample_aspect_ratio(probe_data)
        eff_w = int(w * sar_num / sar_denom)
        src_px = eff_w * h
        target_px = self.config.resolution.width * self.config.resolution.height
        return src_px < target_px

    def __compute_all_bitrate_settings(
        self, probe_data: Dict[str, Any], context: ExecutionContext,
    ) -> Dict[str, float]:
        src_bitrate = FFmpegWrapper.get_video_bitrate(probe_data)
        min_bitrate = self.config.min_bitrate_mbps
        max_bitrate = self.config.video_bitrate_mbps

        if not src_bitrate:
            return self.__build_fallback_bitrates(max_bitrate)

        normalized_bitrate = self.__get_normalized_bitrate(src_bitrate, probe_data, context)

        if normalized_bitrate < min_bitrate:
            final_bitrate = min_bitrate
            adjustment = f"boosted to minimum ({min_bitrate} Mbps)"
        elif normalized_bitrate > max_bitrate:
            final_bitrate = max_bitrate
            adjustment = f"capped to maximum ({max_bitrate} Mbps)"
        else:
            final_bitrate = normalized_bitrate * self.config.bitrate_boost_ratio
            boost_percent = (self.config.bitrate_boost_ratio - 1.0) * 100
            adjustment = f"boosted by {boost_percent:.0f}%"

        context.logger.info(
            f'Bitrate: {src_bitrate:.2f} → {normalized_bitrate:.2f} → {final_bitrate:.2f} Mbps '
            f'({adjustment})',
        )

        return self.__scale_bitrate_limits(final_bitrate / max_bitrate)

    def __get_normalized_bitrate(
        self, src_v: float, probe: Dict[str, Any], context: ExecutionContext,
    ) -> float:
        src_codec = self.__normalize_codec_name(FFmpegWrapper.get_video_codec(probe))
        tgt_codec = self.__normalize_codec_name(self.config.codec)
        mult = self.__get_codec_efficiency_multiplier(src_codec, tgt_codec)

        if mult != 1.0:
            norm = src_v * mult
            context.logger.info(
                f'Codec: {src_codec.upper()}->{tgt_codec.upper()} ({mult:.2f}x) | '
                f'{src_v:.2f}->{norm:.2f} Mbps',
            )
            return norm
        return src_v

    def __scale_bitrate_limits(self, scale: float) -> Dict[str, float]:
        return {
            "video": round(self.config.video_bitrate_mbps * scale, 2),
            "min": round(self.config.calculate_minrate_mbps() * scale, 2),
            "max": round(self.config.calculate_maxrate_mbps() * scale, 2),
            "buf": round(self.config.calculate_bufsize_mbps() * scale, 2),
        }

    def __build_fallback_bitrates(self, target_max: float) -> Dict[str, float]:
        return {
            "video": target_max,
            "min": self.config.calculate_minrate_mbps(),
            "max": self.config.calculate_maxrate_mbps(),
            "buf": self.config.calculate_bufsize_mbps(),
        }

    def __resolve_deinterlacing_strategy(
        self, input_data: SourceVideo, context: ExecutionContext, probe: Dict[str, Any],
    ) -> bool:
        if self.config.force_deinterlace:
            context.logger.info('Deinterlacing: FORCED')
            return True
        has_int, stats = FFmpegWrapper.detect_interlacing(input_data.path)
        if not stats:
            return False

        field_order = FFmpegWrapper.get_field_order(probe)
        ratio_pct = stats['ratio'] * 100

        if has_int:
            context.logger.info(
                f"Interlacing detected ({ratio_pct:.1f}%) | {field_order} → APPLYING deinterlace filter",
            )
        else:
            context.logger.info(f"Interlacing: No ({ratio_pct:.1f}%) | {field_order}")

        return has_int

    def __compute_audio_bitrate(self, probe: Dict[str, Any], context: ExecutionContext) -> int:
        src_a = FFmpegWrapper.get_audio_bitrate(probe)
        tgt_a = self.config.audio_bitrate_kbps
        if src_a and src_a < tgt_a:
            adj = min(int(src_a * 1.05), tgt_a)
            context.logger.info(f'Audio boost: {src_a} -> {adj} kbps')
            return adj
        return tgt_a

    def __execute_ffmpeg_process(
        self, context: ExecutionContext, params: TranscodeParams, ep_id: str,
    ) -> None:
        with StepTempFile(params.output_path) as temp_path:
            temp_params = replace(params, output_path=temp_path)
            context.mark_step_started(self.name, ep_id, [str(temp_path)])

            command_log = FFmpegWrapper.transcode(temp_params)
            if command_log:
                context.logger.info('=' * 20 + ' FFmpeg ' + '=' * 20)
                context.logger.info(command_log)

    def __construct_result_artifact(self, path: Path, input_data: SourceVideo) -> TranscodedVideo:
        return TranscodedVideo(
            path=path,
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            resolution=f'{self.config.resolution.width}x{self.config.resolution.height}',
            codec=self.config.codec,
            source_video_path=input_data.path,
        )

    @staticmethod
    def __should_log_command() -> bool:
        if not VideoTranscoderStep.__command_logged:
            VideoTranscoderStep.__command_logged = True
            return True
        return False

    @staticmethod
    def __normalize_codec_name(codec: str) -> str:
        name = codec.lower()
        mapping = {
            'h264': ('h264', 'avc'),
            'hevc': ('h265', 'hevc'),
            'vp9': ('vp9',),
            'av1': ('av1',),
        }
        for norm, patterns in mapping.items():
            if any(p in name for p in patterns):
                return norm
        return 'h264'

    @staticmethod
    def __get_codec_efficiency_multiplier(src: str, tgt: str) -> float:
        eff = VideoTranscoderStep.__CODEC_EFFICIENCY
        return eff.get(src, 1.0) / eff.get(tgt, 1.0)

    @staticmethod
    def __log_transcode_details(
        ctx: ExecutionContext,
        input_data: SourceVideo,
        params: TranscodeParams,
        probe: Dict[str, Any],
    ) -> None:
        w, h = FFmpegWrapper.get_resolution(probe)
        up_label = "UP" if params.is_upscaling else "DOWN"
        ctx.logger.info(
            f'{input_data.episode_id}: {w}x{h} -> {params.resolution} [{up_label}]',
        )
