from preprocessor.config.step_configs import TranscodeConfig
from preprocessor.core.artifacts import (
    SourceVideo,
    TranscodedVideo,
)
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.lib.media.ffmpeg import FFmpegWrapper


class VideoTranscoderStep(PipelineStep[SourceVideo, TranscodedVideo, TranscodeConfig]):

    @property
    def name(self) -> str:
        return 'video_transcode'

    def execute(  # pylint: disable=too-many-locals,too-many-statements
        self, input_data: SourceVideo, context: ExecutionContext,
    ) -> TranscodedVideo:
        output_filename = f'{context.series_name}_{input_data.episode_info.episode_code()}.mp4'
        output_path = context.get_season_output_path(input_data.episode_info, 'transcoded_videos', output_filename)
        if output_path.exists() and (not context.force_rerun):
            context.logger.info(f'Skipping {input_data.episode_id} (output exists)')
            if not context.is_step_completed(self.name, input_data.episode_id):
                context.mark_step_completed(self.name, input_data.episode_id)
            resolution_str = (
                f'{self.config.resolution.width}x{self.config.resolution.height}'
            )
            return TranscodedVideo(
                path=output_path,
                episode_id=input_data.episode_id,
                episode_info=input_data.episode_info,
                resolution=resolution_str,
                codec=self.config.codec,
            )
        probe_data = FFmpegWrapper.probe_video(input_data.path)
        input_fps = FFmpegWrapper.get_framerate(probe_data)
        input_video_bitrate = FFmpegWrapper.get_video_bitrate(probe_data)
        input_audio_bitrate = FFmpegWrapper.get_audio_bitrate(probe_data)
        target_fps = min(input_fps, 30.0)
        if target_fps < input_fps:
            msg = (
                f'Input FPS ({input_fps}) > 30. '
                f'Limiting to {target_fps} FPS for compatibility and smaller file size.'
            )
            context.logger.info(msg)
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
            msg = (
                f'Input video bitrate ({input_video_bitrate} Mbps) < '
                f'target ({self.config.video_bitrate_mbps} Mbps). '
                f'Adjusted to {video_bitrate} Mbps to avoid quality loss.'
            )
            context.logger.info(msg)
        audio_bitrate = self.config.audio_bitrate_kbps
        if input_audio_bitrate and input_audio_bitrate < audio_bitrate:
            adjusted_audio_bitrate = min(int(input_audio_bitrate * 1.05), audio_bitrate)
            audio_bitrate = adjusted_audio_bitrate
            msg = (
                f'Input audio bitrate ({input_audio_bitrate} kbps) < '
                f'target ({self.config.audio_bitrate_kbps} kbps). '
                f'Adjusted to {audio_bitrate} kbps to avoid quality loss.'
            )
            context.logger.info(msg)
        if self.config.force_deinterlace:
            context.logger.info(
                f"Force deinterlacing enabled for {input_data.episode_id} - "
                f"skipping interlace detection and applying bwdif filter unconditionally",
            )
            deinterlace = True
        else:
            context.logger.info(f"Detecting interlacing for {input_data.episode_id}...")
            has_interlacing, idet_stats = FFmpegWrapper.detect_interlacing(input_data.path)
            if has_interlacing and idet_stats:
                context.logger.info(
                    f"Interlacing detected for {input_data.episode_id} "
                    f"({idet_stats['ratio']*100:.1f}% interlaced frames: "
                    f"TFF={idet_stats['tff']}, BFF={idet_stats['bff']}) - "
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
            deinterlace = has_interlacing
        context.logger.info(f'Transcoding {input_data.episode_id}')
        temp_path = output_path.with_suffix('.mp4.tmp')
        context.mark_step_started(self.name, input_data.episode_id, [str(temp_path)])
        try:
            FFmpegWrapper.transcode(
                input_path=input_data.path,
                output_path=temp_path,
                codec=self.config.codec,
                preset=self.config.preset,
                resolution=f'{self.config.resolution.width}:{self.config.resolution.height}',
                video_bitrate=f'{video_bitrate}M',
                minrate=f'{minrate}M',
                maxrate=f'{maxrate}M',
                bufsize=f'{bufsize}M',
                audio_bitrate=f'{audio_bitrate}k',
                gop_size=int(target_fps * self.config.gop_size),
                target_fps=target_fps if target_fps < input_fps else None,
                deinterlace=deinterlace,
            )
            temp_path.replace(output_path)
        except BaseException:
            if temp_path.exists():
                temp_path.unlink()
            raise
        context.mark_step_completed(self.name, input_data.episode_id)
        resolution_str = f'{self.config.resolution.width}x{self.config.resolution.height}'
        return TranscodedVideo(
            path=output_path,
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            resolution=resolution_str,
            codec=self.config.codec,
        )
