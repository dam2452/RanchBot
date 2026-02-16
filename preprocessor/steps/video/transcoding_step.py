from dataclasses import replace
import math
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Tuple,
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
    __command_logged: bool = False

    @property
    def name(self) -> str:
        return 'video_transcode'

    @property
    def supports_batch_processing(self) -> bool:
        return True

    def execute_batch(
        self, input_data: List[SourceVideo], context: ExecutionContext,
    ) -> List[TranscodedVideo]:
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

    def _get_output_descriptors(self) -> List[FileOutput]:
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
        target_fps = self.__resolve_target_framerate()
        is_upscaling, src_px, target_px = self.__analyze_resolution_scaling(probe_data)

        bitrates = self.__compute_all_bitrate_settings(
            probe_data, context, is_upscaling, src_px, target_px,
        )

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

    def __analyze_resolution_scaling(self, probe_data: Dict[str, Any]) -> Tuple[bool, int, int]:
        w, h = FFmpegWrapper.get_resolution(probe_data)
        sar_num, sar_denom = FFmpegWrapper.get_sample_aspect_ratio(probe_data)

        eff_w = int(w * sar_num / sar_denom)
        src_px = eff_w * h
        target_px = self.config.resolution.width * self.config.resolution.height

        return src_px < target_px, src_px, target_px

    def __compute_all_bitrate_settings(
        self,
        probe_data: Dict[str, Any],
        context: ExecutionContext,
        is_up: bool,
        src_px: int,
        target_px: int,
    ) -> Dict[str, float]:
        src_v = FFmpegWrapper.get_video_bitrate(probe_data)
        target_max = self.config.video_bitrate_mbps

        if not src_v:
            return self.__build_fallback_bitrates(target_max)

        norm_v = self.__get_normalized_bitrate(src_v, probe_data, is_up, context)
        ratio = target_px / src_px
        exp = self.__calculate_scaling_exponent(ratio, is_up)

        scaled_raw = norm_v * (ratio**exp)
        scaled_min = self.__apply_min_upscale_constraint(scaled_raw, target_max, is_up)
        final_v = min(scaled_min, target_max)

        self.__log_bitrate_workflow(
            context, src_v, norm_v, scaled_raw, scaled_min, final_v, target_max, ratio, is_up,
        )

        return self.__scale_bitrate_limits(final_v / target_max)

    def __get_normalized_bitrate(
        self, src_v: float, probe: Dict[str, Any], is_up: bool, context: ExecutionContext,
    ) -> float:
        if not is_up:
            return src_v

        src_codec = self.__normalize_codec_name(FFmpegWrapper.get_video_codec(probe))
        tgt_codec = self.__normalize_codec_name(self.config.codec)
        mult = self.__get_codec_efficiency_multiplier(src_codec, tgt_codec)

        if mult != 1.0:
            norm = src_v * mult
            context.logger.info(
                f'Codec: {src_codec.upper()}->{tgt_codec.upper()} ({mult}x) | '
                f'{src_v:.2f}->{norm:.2f} Mbps',
            )
            return norm
        return src_v

    def __apply_min_upscale_constraint(self, scaled: float, target_max: float, is_up: bool) -> float:
        if not is_up:
            return scaled
        return max(scaled, target_max * self.config.min_upscale_bitrate_ratio)

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
            return True
        has_int, stats = FFmpegWrapper.detect_interlacing(input_data.path)
        if not stats:
            return False
        self.__log_int_diagnostics(context, has_int, stats, FFmpegWrapper.get_field_order(probe))
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

            if temp_params.log_command:
                context.logger.info('=' * 20 + ' FFmpeg ' + '=' * 20)
            FFmpegWrapper.transcode(temp_params)

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
    def __calculate_scaling_exponent(ratio: float, is_up: bool) -> float:
        log_r = math.log10(max(ratio, 0.01))
        if is_up:
            return 0.8 + min(log_r, 1.0) * 0.35
        return 0.8 + max(log_r, -2.0) * 0.175

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
    def __log_bitrate_workflow(
        ctx: ExecutionContext,
        src: float,
        norm: float,
        raw: float,
        s_min: float,
        final: float,
        limit: float,
        ratio: float,
        is_up: bool,
    ) -> None:
        dir_label = "upscaling" if is_up else ("downscaling" if ratio < 1.0 else "same")
        min_msg = f' (MinBoost: {s_min:.2f})' if is_up and (s_min > raw) else ''
        ctx.logger.info(
            f'[{dir_label}] {src:.2f}->{norm:.2f}->{raw:.2f}{min_msg} -> {final:.2f} Mbps '
            f'(Max: {limit})',
        )

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

    @staticmethod
    def __log_int_diagnostics(ctx: ExecutionContext, has_int: bool, stats: Dict[str, float], order: str) -> None:
        ctx.logger.info(f"Interlacing: {has_int} ({stats['ratio'] * 100:.1f}%) | {order}")

    @staticmethod
    def __resolve_target_framerate() -> float:
        return 24.0
