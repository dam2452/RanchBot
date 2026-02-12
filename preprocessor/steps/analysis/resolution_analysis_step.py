from collections import Counter
from datetime import datetime
import json
from pathlib import Path
from typing import List

from preprocessor.config.step_configs import TranscodeConfig
from preprocessor.core.artifacts import ResolutionAnalysisResult
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.services.io.path_service import PathService
from preprocessor.services.media.ffmpeg import FFmpegWrapper


class ResolutionAnalysisStep(PipelineStep[None, ResolutionAnalysisResult, TranscodeConfig]):

    def execute(
        self, input_data: None, context: ExecutionContext,
    ) -> ResolutionAnalysisResult:
        context.logger.info('=' * 80)
        context.logger.info('RESOLUTION ANALYSIS - Checking source video resolutions')
        context.logger.info('=' * 80)

        video_paths = self.__find_video_files(context)
        if not video_paths:
            context.logger.warning('No video files found - skipping resolution analysis')
            context.mark_step_completed(self.name, 'all')
            return ResolutionAnalysisResult(total_files=0, upscaling_percentage=0.0)

        resolutions = self.__scan_resolutions(video_paths, context)
        if not resolutions:
            context.logger.warning('Failed to analyze resolutions - skipping')
            context.mark_step_completed(self.name, 'all')
            return ResolutionAnalysisResult(total_files=len(video_paths), upscaling_percentage=0.0)

        upscaling_pct = self.__analyze_and_report(resolutions, context)
        self.__save_results_to_json(resolutions, upscaling_pct, context)

        context.mark_step_completed(self.name, 'all')
        return ResolutionAnalysisResult(total_files=len(resolutions), upscaling_percentage=upscaling_pct)

    @property
    def name(self) -> str:
        return 'resolution_analysis'

    @property
    def is_global(self) -> bool:
        return True

    @staticmethod
    def __find_video_files(context: ExecutionContext) -> List[Path]:
        input_base = PathService.get_input_base()
        series_path = input_base / context.series_name

        if not series_path.exists():
            return []

        video_extensions = {'.mp4', '.mkv', '.avi', '.mov', '.m4v'}
        video_files = [
            p for p in series_path.rglob('*')
            if p.is_file() and p.suffix.lower() in video_extensions
        ]

        return sorted(video_files)

    @staticmethod
    def __scan_resolutions(
        video_paths: List[Path], context: ExecutionContext,
    ) -> List[tuple[int, int, str]]:
        resolutions = []

        for video_path in video_paths:
            try:
                probe_data = FFmpegWrapper.probe_video(video_path)
                width, height = FFmpegWrapper.get_resolution(probe_data)
                sar_num, sar_denom = FFmpegWrapper.get_sample_aspect_ratio(probe_data)

                effective_width = int(width * sar_num / sar_denom)
                resolutions.append((effective_width, height, video_path.name))

            except Exception as e:  # pylint: disable=broad-except
                context.logger.warning(f'Failed to probe {video_path.name}: {e}')
                continue

        return resolutions

    def __analyze_and_report(
        self, resolutions: List[tuple[int, int, str]], context: ExecutionContext,
    ) -> float:
        resolution_counts = Counter((w, h) for w, h, _ in resolutions)
        total_episodes = len(resolutions)

        target_width = self.config.resolution.width
        target_height = self.config.resolution.height
        target_pixels = target_width * target_height

        upscaling_count = sum(
            1 for w, h, _ in resolutions
            if (w * h) < target_pixels
        )
        upscaling_pct = (upscaling_count / total_episodes) * 100 if total_episodes > 0 else 0

        context.logger.info('')
        context.logger.info('Source Resolution Distribution:')
        context.logger.info('-' * 60)

        for (width, height), count in resolution_counts.most_common():
            pct = (count / total_episodes) * 100
            label = self.__get_resolution_label(width, height)
            context.logger.info(
                f'  {width}x{height} ({label}): {count} episodes ({pct:.1f}%)',
            )

        context.logger.info('')
        context.logger.info(
            f'Target Resolution: {target_width}x{target_height} '
            f'({self.__get_resolution_label(target_width, target_height)})',
        )

        if upscaling_pct > 50:
            context.logger.warning('')
            context.logger.warning('⚠' * 30)
            context.logger.warning(
                f'⚠ WARNING: {upscaling_pct:.1f}% of episodes will require UPSCALING!',
            )
            context.logger.warning(
                '⚠ Upscaling degrades quality. Consider using analyze-resolution CLI '
                'to find optimal target resolution.',
            )
            context.logger.warning('⚠' * 30)
        elif upscaling_pct > 0:
            context.logger.info(
                f'Note: {upscaling_pct:.1f}% of episodes will be upscaled '
                '(enhanced quality params will be used)',
            )

        context.logger.info('=' * 80)

        return upscaling_pct

    @staticmethod
    def __get_resolution_label(width: int, height: int) -> str:
        resolution_labels = {
            (7680, 4320): '8K',
            (3840, 2160): '4K',
            (2560, 1440): '1440p',
            (1920, 1080): '1080p',
            (1280, 720): '720p',
            (854, 480): '480p',
            (640, 360): '360p',
            (426, 240): '240p',
            (256, 144): '144p',
        }

        if (width, height) in resolution_labels:
            return resolution_labels[(width, height)]

        if height >= 2000:
            return '4K+'
        if height >= 1400:
            return '2K'
        if height >= 1000:
            return 'Full HD'
        if height >= 700:
            return 'HD'
        if height >= 450:
            return 'SD'
        return 'Low'

    def __save_results_to_json(
        self,
        resolutions: List[tuple[int, int, str]],
        upscaling_pct: float,
        context: ExecutionContext,
    ) -> None:
        output_base = PathService.get_output_base()
        output_dir = output_base / context.series_name
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / 'resolution_analysis.json'

        resolution_counts = Counter((w, h) for w, h, _ in resolutions)
        total_episodes = len(resolutions)

        target_width = self.config.resolution.width
        target_height = self.config.resolution.height
        target_pixels = target_width * target_height

        upscaling_count = sum(
            1 for w, h, _ in resolutions
            if (w * h) < target_pixels
        )

        source_resolutions = [
            {
                'width': width,
                'height': height,
                'count': count,
                'percentage': round((count / total_episodes) * 100, 1),
                'label': self.__get_resolution_label(width, height),
            }
            for (width, height), count in resolution_counts.most_common()
        ]

        files_details = [
            {
                'filename': filename,
                'width': width,
                'height': height,
                'label': self.__get_resolution_label(width, height),
                'needs_upscaling': (width * height) < target_pixels,
            }
            for width, height, filename in sorted(resolutions, key=lambda x: x[2])
        ]

        result = {
            'analysis_date': datetime.now().isoformat(),
            'series_name': context.series_name,
            'target_resolution': {
                'width': target_width,
                'height': target_height,
                'label': self.__get_resolution_label(target_width, target_height),
            },
            'source_resolutions': source_resolutions,
            'total_files': total_episodes,
            'upscaling_required': {
                'count': upscaling_count,
                'percentage': round(upscaling_pct, 1),
            },
            'files': files_details,
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        context.logger.info(f'Resolution analysis saved to: {output_file}')
