from pathlib import Path
from typing import (
    Any,
    Dict,
    Tuple,
)

from preprocessor.config.step_configs import TranscodeConfig
from preprocessor.core.artifacts import (
    SourceVideo,
    TranscodedVideo,
)
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.services.media.ffmpeg import FFmpegWrapper
from preprocessor.services.media.transcode_params import TranscodeParams


class VideoTranscoderStep(PipelineStep[SourceVideo, TranscodedVideo, TranscodeConfig]):
    __command_logged = False

    @property
    def name(self) -> str:
        return 'video_transcode'

    def execute(
            self, input_data: SourceVideo, context: ExecutionContext,
    ) -> TranscodedVideo:
        output_path = self.__resolve_output_path(input_data, context)

        if self._check_cache_validity(output_path, context, input_data.episode_id, 'output exists'):
            return self.__construct_result_artifact(output_path, input_data)

        probe_data = FFmpegWrapper.probe_video(input_data.path)
        params = self.__create_transcode_params(input_data, output_path, probe_data, context)

        self.__log_transcode_details(context, input_data, params, probe_data)
        self.__execute_ffmpeg_process(context, params, input_data.episode_id)

        context.mark_step_completed(self.name, input_data.episode_id)
        return self.__construct_result_artifact(output_path, input_data)

    def __create_transcode_params(
            self,
            input_data: SourceVideo,
            output_path: Path,
            probe_data: Dict[str, Any],
            context: ExecutionContext,
    ) -> TranscodeParams:
        target_fps = self.__resolve_target_framerate(probe_data, context)
        is_upscaling, source_pixels, target_pixels = self.__analyze_resolution_scaling(probe_data)

        v_bitrate, v_min, v_max, v_buf = self.__compute_video_bitrate_settings(
            probe_data, context, is_upscaling, source_pixels, target_pixels,
        )

        audio_bitrate = self.__compute_audio_bitrate(probe_data, context)
        deinterlace = self.__resolve_deinterlacing_strategy(input_data, context, probe_data)
        log_cmd = self.__should_log_command()

        return TranscodeParams(
            input_path=input_data.path,
            output_path=output_path,
            codec=self.config.codec,
            preset=self.config.preset,
            resolution=f'{self.config.resolution.width}:{self.config.resolution.height}',
            video_bitrate=f'{v_bitrate}M',
            minrate=f'{v_min}M',
            maxrate=f'{v_max}M',
            bufsize=f'{v_buf}M',
            audio_bitrate=f'{audio_bitrate}k',
            gop_size=int(target_fps * self.config.keyframe_interval_seconds),
            target_fps=target_fps,
            deinterlace=deinterlace,
            is_upscaling=is_upscaling,
            log_command=log_cmd,
        )

    def __analyze_resolution_scaling(
            self,
            probe_data: Dict[str, Any],
    ) -> Tuple[bool, int, int]:
        source_width, source_height = FFmpegWrapper.get_resolution(probe_data)
        sar_num, sar_denom = FFmpegWrapper.get_sample_aspect_ratio(probe_data)
        effective_width = int(source_width * sar_num / sar_denom)

        source_pixels = effective_width * source_height
        target_pixels = self.config.resolution.width * self.config.resolution.height

        return source_pixels < target_pixels, source_pixels, target_pixels

    def __compute_video_bitrate_settings(
            self,
            probe_data: Dict[str, Any],
            context: ExecutionContext,
            is_upscaling: bool,
            source_pixels: int,
            target_pixels: int,
    ) -> Tuple[float, float, float, float]:
        return self.__compute_scaled_bitrate(
            probe_data, source_pixels, target_pixels, context, is_upscaling,
        )

    def __compute_scaled_bitrate(
            self,
            probe_data: Dict[str, Any],
            source_pixels: int,
            target_pixels: int,
            context: ExecutionContext,
            is_upscaling: bool,
    ) -> Tuple[float, float, float, float]:
        source_bitrate = FFmpegWrapper.get_video_bitrate(probe_data)
        target_bitrate = self.config.calculate_video_bitrate_mbps()
        minrate = self.config.calculate_minrate_mbps()
        maxrate = self.config.calculate_maxrate_mbps()
        bufsize = self.config.calculate_bufsize_mbps()

        if not source_bitrate:
            context.logger.warning(
                f'Cannot detect source bitrate. Using target bitrate ({target_bitrate} Mbps).',
            )
            return target_bitrate, minrate, maxrate, bufsize

        pixel_ratio = target_pixels / source_pixels
        scaled_bitrate = source_bitrate * (pixel_ratio ** 0.7)

        final_bitrate = min(scaled_bitrate, target_bitrate)
        ratio = final_bitrate / target_bitrate

        direction = 'upscaling' if is_upscaling else 'downscaling' if pixel_ratio < 1.0 else 'same resolution'
        context.logger.info(
            f'Bitrate calculation ({direction}): '
            f'source {source_bitrate:.2f} Mbps @ {source_pixels:,}px → '
            f'scaled {scaled_bitrate:.2f} Mbps @ {target_pixels:,}px '
            f'(pixel_ratio {pixel_ratio:.2f}, exponent 0.7) → '
            f'final {final_bitrate:.2f} Mbps (capped to target {target_bitrate} Mbps)',
        )

        return (
            final_bitrate,
            round(minrate * ratio, 2),
            round(maxrate * ratio, 2),
            round(bufsize * ratio, 2),
        )

    def __compute_audio_bitrate(
            self,
            probe_data: Dict[str, Any],
            context: ExecutionContext,
    ) -> int:
        input_audio = FFmpegWrapper.get_audio_bitrate(probe_data)
        target_audio = self.config.audio_bitrate_kbps

        if input_audio and input_audio < target_audio:
            adjusted = min(int(input_audio * 1.05), target_audio)
            context.logger.info(
                f'Input audio ({input_audio} kbps) < target. Adjusted to {adjusted} kbps.',
            )
            return adjusted
        return target_audio

    def __resolve_deinterlacing_strategy(
            self,
            input_data: SourceVideo,
            context: ExecutionContext,
            probe_data: Dict[str, Any],
    ) -> bool:
        if self.config.force_deinterlace:
            context.logger.info(f"Force deinterlacing enabled for {input_data.episode_id}")
            return True

        return self.__detect_and_verify_interlacing(input_data, context, probe_data)

    def __log_execution_details(
            self,
            context: ExecutionContext,
            input_data: SourceVideo,
            params: TranscodeParams,
            probe_data: Dict[str, Any],
    ) -> None:
        source_w, source_h = FFmpegWrapper.get_resolution(probe_data)
        upscale_msg = "UPSCALING DETECTED" if params.is_upscaling else "No upscaling"

        context.logger.info(
            f'{input_data.episode_id}: Source {source_w}x{source_h} → '
            f'Target {self.config.resolution.width}x{self.config.resolution.height} - {upscale_msg}',
        )
        self.__log_static_transcode_info(context, params.audio_bitrate)
        context.logger.info(f'Transcoding {input_data.episode_id}')

    def __log_transcode_details(
            self,
            context: ExecutionContext,
            input_data: SourceVideo,
            params: TranscodeParams,
            probe_data: Dict[str, Any],
    ) -> None:
        self.__log_execution_details(context, input_data, params, probe_data)

    def __execute_ffmpeg_process(
            self,
            context: ExecutionContext,
            params: TranscodeParams,
            episode_id: str,
    ) -> None:
        temp_path = params.output_path.with_suffix('.mp4.tmp')
        final_path = params.output_path

        params.output_path = temp_path
        context.mark_step_started(self.name, episode_id, [str(temp_path)])

        try:
            if params.log_command:
                self.__log_ffmpeg_command_header(context)

            FFmpegWrapper.transcode(params)
            temp_path.replace(final_path)
        except BaseException:
            if temp_path.exists():
                temp_path.unlink()
            raise
        finally:
            params.output_path = final_path

    def __construct_result_artifact(
            self,
            output_path: Path,
            input_data: SourceVideo,
    ) -> TranscodedVideo:
        return TranscodedVideo(
            path=output_path,
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            resolution=f'{self.config.resolution.width}x{self.config.resolution.height}',
            codec=self.config.codec,
        )

    @staticmethod
    def __should_log_command() -> bool:
        if not VideoTranscoderStep.__command_logged:
            VideoTranscoderStep.__command_logged = True
            return True
        return False

    @staticmethod
    def __resolve_output_path(
            input_data: SourceVideo,
            context: ExecutionContext,
    ) -> Path:
        filename = f'{context.series_name}_{input_data.episode_info.episode_code()}.mp4'
        return context.get_season_output_path(
            input_data.episode_info, 'transcoded_videos', filename,
        )

    @staticmethod
    def __resolve_target_framerate(
            probe_data: Dict[str, Any],
            context: ExecutionContext,
    ) -> float:
        input_fps = FFmpegWrapper.get_framerate(probe_data)
        target_fps = 24.0

        if input_fps != target_fps:
            context.logger.info(
                f'Input FPS ({input_fps:.2f}) → forcing {target_fps} FPS for consistency.',
            )
        return target_fps

    @staticmethod
    def __detect_and_verify_interlacing(
            input_data: SourceVideo,
            context: ExecutionContext,
            probe_data: Dict[str, Any],
    ) -> bool:
        context.logger.info(f"Detecting interlacing for {input_data.episode_id}...")
        has_interlacing, idet_stats = FFmpegWrapper.detect_interlacing(input_data.path)
        field_order = FFmpegWrapper.get_field_order(probe_data)

        if not idet_stats:
            context.logger.error(
                f"Failed to detect interlacing for {input_data.episode_id}. Proceeding without deinterlace.",
            )
            return False

        VideoTranscoderStep.__log_interlacing_diagnostics(context, has_interlacing, idet_stats, field_order)
        return has_interlacing

    @staticmethod
    def __log_interlacing_diagnostics(
            context: ExecutionContext,
            has_interlacing: bool,
            idet_stats: Dict[str, Any],
            field_order: str,
    ) -> None:
        meta_progressive = field_order in {'progressive', 'unknown'}
        idet_progressive = not has_interlacing

        if meta_progressive != idet_progressive:
            context.logger.warning(
                f"⚠ Conflict: Metadata says {field_order}, idet says "
                f"{'interlaced' if has_interlacing else 'progressive'}. Using idet result.",
            )

        if has_interlacing:
            context.logger.info(
                f"Interlacing detected ({idet_stats['ratio'] * 100:.1f}%). Applying bwdif.",
            )
        else:
            context.logger.info("Progressive content detected. No deinterlacing needed.")

    @staticmethod
    def __log_static_transcode_info(context: ExecutionContext, audio_bitrate: str) -> None:
        context.logger.info(
            'Video: SAR 1:1, timebase 1/90000, colorspace bt709, '
            'closed GOP=12 frames with IDR keyframes.',
        )
        context.logger.info(
            f'Audio: AAC {audio_bitrate}, 2 channels, 48 kHz (forced).',
        )

    @staticmethod
    def __log_ffmpeg_command_header(context: ExecutionContext) -> None:
        context.logger.info('=' * 80)
        context.logger.info('FFmpeg command example (showing once):')
        context.logger.info('=' * 80)
