from pathlib import Path
from typing import (
    Any,
    Dict,
)

from preprocessor.config.step_configs import TranscodeConfig
from preprocessor.core.artifacts import (
    SourceVideo,
    TranscodedVideo,
)
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.services.media.ffmpeg import FFmpegWrapper


class VideoTranscoderStep(PipelineStep[SourceVideo, TranscodedVideo, TranscodeConfig]):
    _command_logged = False

    def execute( # pylint: disable=too-many-locals
        self, input_data: SourceVideo, context: ExecutionContext,
    ) -> TranscodedVideo:
        output_path = self._get_output_path(input_data, context)

        if self._check_cache_validity(output_path, context, input_data.episode_id, 'output exists'):
            return self._create_result_artifact(output_path, input_data)

        probe_data = FFmpegWrapper.probe_video(input_data.path)
        target_fps = self._calculate_target_fps(probe_data, context)
        is_upscaling, source_pixels, target_pixels = self._detect_upscaling(probe_data)

        source_width, source_height = FFmpegWrapper.get_resolution(probe_data)
        sar_num, sar_denom = FFmpegWrapper.get_sample_aspect_ratio(probe_data)
        effective_width = int(source_width * sar_num / sar_denom)

        if is_upscaling:
            context.logger.info(
                f'{input_data.episode_id}: Source {effective_width}x{source_height} '
                f'({source_pixels:,} px) → Target {self.config.resolution.width}x{self.config.resolution.height} '
                f'({target_pixels:,} px) - UPSCALING DETECTED',
            )
        else:
            context.logger.info(
                f'{input_data.episode_id}: Source {effective_width}x{source_height} '
                f'({source_pixels:,} px) → Target {self.config.resolution.width}x{self.config.resolution.height} '
                f'({target_pixels:,} px) - No upscaling',
            )

        video_bitrate, minrate, maxrate, bufsize = self._adjust_video_bitrate(
            probe_data, context, is_upscaling, source_pixels, target_pixels,
        )
        audio_bitrate = self._adjust_audio_bitrate(probe_data, context)
        deinterlace = self._determine_deinterlace(input_data, context, probe_data)

        context.logger.info(
            'Video: SAR 1:1 (square pixels), timebase 1/90000, '
            'colorspace bt709, color_range tv, closed GOP=12 frames (0.5s) with IDR keyframes '
            '(forced for frame-accurate cutting & concat)',
        )
        context.logger.info(
            f'Audio: AAC {audio_bitrate} kbps, 2 channels (stereo), 48 kHz sample rate (forced)',
        )
        context.logger.info(f'Transcoding {input_data.episode_id}')
        self._perform_transcode(
            input_data.path,
            output_path,
            video_bitrate,
            minrate,
            maxrate,
            bufsize,
            audio_bitrate,
            target_fps,
            deinterlace,
            is_upscaling,
            context,
            input_data,
        )

        context.mark_step_completed(self.name, input_data.episode_id)
        return self._create_result_artifact(output_path, input_data)

    @property
    def name(self) -> str:
        return 'video_transcode'

    @staticmethod
    def _get_output_path(input_data: SourceVideo, context: ExecutionContext) -> Path:
        output_filename = f'{context.series_name}_{input_data.episode_info.episode_code()}.mp4'
        return context.get_season_output_path(input_data.episode_info, 'transcoded_videos', output_filename)


    def _create_result_artifact(self, output_path: Path, input_data: SourceVideo) -> TranscodedVideo:
        resolution_str = f'{self.config.resolution.width}x{self.config.resolution.height}'
        return TranscodedVideo(
            path=output_path,
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            resolution=resolution_str,
            codec=self.config.codec,
        )

    @staticmethod
    def _calculate_target_fps(
        probe_data: Dict[str, Any],
        context: ExecutionContext,
    ) -> float:
        input_fps = FFmpegWrapper.get_framerate(probe_data)
        target_fps = 24.0

        if input_fps != target_fps:
            context.logger.info(
                f'Input FPS ({input_fps:.2f}) → forcing {target_fps} FPS for consistency and cinematic quality.',
            )

        return target_fps

    def _detect_upscaling(self, probe_data: Dict[str, Any]) -> tuple[bool, int, int]:
        source_width, source_height = FFmpegWrapper.get_resolution(probe_data)
        sar_num, sar_denom = FFmpegWrapper.get_sample_aspect_ratio(probe_data)
        effective_width = int(source_width * sar_num / sar_denom)

        source_pixels = effective_width * source_height
        target_pixels = self.config.resolution.width * self.config.resolution.height

        return source_pixels < target_pixels, source_pixels, target_pixels

    def _adjust_video_bitrate(
        self,
        probe_data: Dict[str, Any],
        context: ExecutionContext,
        is_upscaling: bool,
        source_pixels: int,
        target_pixels: int,
    ) -> tuple[float, float, float, float]:
        if is_upscaling:
            return self._calculate_upscale_bitrate(
                probe_data, source_pixels, target_pixels, context,
            )

        input_video_bitrate = FFmpegWrapper.get_video_bitrate(probe_data)
        video_bitrate = self.config.video_bitrate_mbps
        minrate = self.config.minrate_mbps
        maxrate = self.config.maxrate_mbps
        bufsize = self.config.bufsize_mbps

        if input_video_bitrate and input_video_bitrate < video_bitrate:
            adjusted_bitrate = min(input_video_bitrate * 1.05, video_bitrate)
            ratio = adjusted_bitrate / video_bitrate
            video_bitrate = adjusted_bitrate
            minrate = round(minrate * ratio, 2)
            maxrate = round(maxrate * ratio, 2)
            bufsize = round(bufsize * ratio, 2)
            context.logger.info(
                f'Input video bitrate ({input_video_bitrate} Mbps) < '
                f'target ({self.config.video_bitrate_mbps} Mbps). '
                f'Adjusted to {video_bitrate} Mbps to avoid quality loss.',
            )

        return video_bitrate, minrate, maxrate, bufsize

    def _calculate_upscale_bitrate(
        self,
        probe_data: Dict[str, Any],
        source_pixels: int,
        target_pixels: int,
        context: ExecutionContext,
    ) -> tuple[float, float, float, float]:
        __MIN_BITRATE_FOR_RESOLUTION: Dict[tuple[int, int], float] = {
            (7680, 4320): 35.0,
            (3840, 2160): 15.0,
            (2560, 1440): 8.0,
            (1920, 1080): 3.5,
            (1280, 720): 2.0,
            (854, 480): 1.2,
            (640, 360): 0.8,
            (426, 240): 0.5,
            (256, 144): 0.3,
        }

        target_res = (self.config.resolution.width, self.config.resolution.height)
        min_required = __MIN_BITRATE_FOR_RESOLUTION.get(target_res, 2.0)
        pixel_ratio = target_pixels / source_pixels

        if pixel_ratio > 1.4:
            min_required *= 1.25
        elif pixel_ratio > 1.2:
            min_required *= 1.15

        source_bitrate = FFmpegWrapper.get_video_bitrate(probe_data)
        quality_boost = 1.2 + max(0.0, (pixel_ratio - 1.1) * 0.4)

        if source_bitrate:
            calculated = source_bitrate * pixel_ratio * quality_boost
            upscaled_bitrate = max(calculated, min_required)
        else:
            upscaled_bitrate = min_required * max(1.2, pixel_ratio * 0.9)

        max_allowed = self.config.video_bitrate_mbps * 1.3
        upscaled_bitrate = min(upscaled_bitrate, max_allowed)

        ratio = upscaled_bitrate / self.config.video_bitrate_mbps

        context.logger.warning(
            f'⚠ UPSCALING: {source_pixels:,} px → {target_pixels:,} px '
            f'(+{((target_pixels/source_pixels)-1)*100:.1f}%, quality_boost={quality_boost:.2f}). '
            f'Bitrate: {source_bitrate or "N/A"} → {upscaled_bitrate:.2f} Mbps '
            f'(min for {target_res[0]}x{target_res[1]}: {min_required} Mbps). '
            f'Using Spline36 scaler (flicker-free) + enhanced nvenc params.',
        )

        return (
            upscaled_bitrate,
            round(self.config.minrate_mbps * ratio, 2),
            round(self.config.maxrate_mbps * ratio, 2),
            round(self.config.bufsize_mbps * ratio, 2),
        )

    def _adjust_audio_bitrate(
        self,
        probe_data: Dict[str, Any],
        context: ExecutionContext,
    ) -> int:
        input_audio_bitrate = FFmpegWrapper.get_audio_bitrate(probe_data)
        audio_bitrate = self.config.audio_bitrate_kbps

        if input_audio_bitrate and input_audio_bitrate < audio_bitrate:
            adjusted_audio_bitrate = min(int(input_audio_bitrate * 1.05), audio_bitrate)
            audio_bitrate = adjusted_audio_bitrate
            context.logger.info(
                f'Input audio bitrate ({input_audio_bitrate} kbps) < '
                f'target ({self.config.audio_bitrate_kbps} kbps). '
                f'Adjusted to {audio_bitrate} kbps to avoid quality loss.',
            )

        return audio_bitrate

    def _determine_deinterlace(
        self, input_data: SourceVideo, context: ExecutionContext, probe_data: Dict[str, Any],
    ) -> bool:
        field_order = FFmpegWrapper.get_field_order(probe_data)

        if self.config.force_deinterlace:
            context.logger.info(
                f"Force deinterlacing enabled for {input_data.episode_id} (field_order={field_order}) - "
                f"skipping idet analysis and applying bwdif filter unconditionally",
            )
            return True

        context.logger.info(
            f"Detecting interlacing for {input_data.episode_id} "
            f"(field_order={field_order}, analyzing first 60s)...",
        )
        has_interlacing, idet_stats = FFmpegWrapper.detect_interlacing(input_data.path)

        if idet_stats:
            metadata_says_progressive = field_order in {'progressive', 'unknown'}
            idet_says_progressive = not has_interlacing

            if metadata_says_progressive != idet_says_progressive:
                context.logger.warning(
                    f"⚠ {input_data.episode_id}: field_order={field_order} but idet detected "
                    f"{'interlaced' if has_interlacing else 'progressive'} content! Using idet result.",
                )

        if has_interlacing and idet_stats:
            context.logger.info(
                f"Interlacing detected for {input_data.episode_id} "
                f"({idet_stats['ratio']*100:.1f}% interlaced frames: "
                f"TFF={idet_stats['tff']}, BFF={idet_stats['bff']}, Progressive={idet_stats['progressive']}) - "
                f"applying bwdif deinterlacing filter",
            )
        elif idet_stats:
            context.logger.info(
                f"Progressive content detected for {input_data.episode_id} "
                f"({idet_stats['progressive']}/{idet_stats['progressive'] + idet_stats['tff'] + idet_stats['bff']} frames) - "
                f"no deinterlacing needed",
            )
        else:
            context.logger.error(
                f"Failed to detect interlacing for {input_data.episode_id} - "
                f"idet filter did not return valid statistics. "
                f"This may indicate an ffmpeg error or incompatible video format. "
                f"Proceeding without deinterlacing.",
            )

        return has_interlacing

    def _perform_transcode(  # pylint: disable=too-many-arguments
        self,
        input_path: Path,
        output_path: Path,
        video_bitrate: float,
        minrate: float,
        maxrate: float,
        bufsize: float,
        audio_bitrate: int,
        target_fps: float,
        deinterlace: bool,
        is_upscaling: bool,
        context: ExecutionContext,
        input_data: SourceVideo,
    ) -> None:
        temp_path = output_path.with_suffix('.mp4.tmp')
        context.mark_step_started(self.name, input_data.episode_id, [str(temp_path)])

        try:
            log_command = not VideoTranscoderStep._command_logged
            if log_command:
                VideoTranscoderStep._command_logged = True
                context.logger.info('=' * 80)
                context.logger.info('FFmpeg command example (showing once):')
                context.logger.info('=' * 80)

            FFmpegWrapper.transcode(
                input_path=input_path,
                output_path=temp_path,
                codec=self.config.codec,
                preset=self.config.preset,
                resolution=f'{self.config.resolution.width}:{self.config.resolution.height}',
                video_bitrate=f'{video_bitrate}M',
                minrate=f'{minrate}M',
                maxrate=f'{maxrate}M',
                bufsize=f'{bufsize}M',
                audio_bitrate=f'{audio_bitrate}k',
                gop_size=int(target_fps * 0.5),
                target_fps=target_fps,
                deinterlace=deinterlace,
                is_upscaling=is_upscaling,
                log_command=log_command,
            )
            temp_path.replace(output_path)
        except BaseException:
            if temp_path.exists():
                temp_path.unlink()
            raise
