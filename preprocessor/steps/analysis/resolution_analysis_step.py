from collections import Counter
from datetime import datetime
import json
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from preprocessor.config.step_configs import TranscodeConfig
from preprocessor.core.artifacts import ResolutionAnalysisResult
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.services.io.path_service import PathService
from preprocessor.services.media.ffmpeg import FFmpegWrapper


class ResolutionAnalysisStep(PipelineStep[None, ResolutionAnalysisResult, TranscodeConfig]):
    @property
    def name(self) -> str:
        return 'resolution_analysis'

    @property
    def is_global(self) -> bool:
        return True

    def execute(
            self, input_data: None, context: ExecutionContext,
    ) -> ResolutionAnalysisResult:
        self.__log_analysis_header(context)

        video_paths = self.__find_video_files(context)
        if not video_paths:
            return self.__handle_missing_videos(context)

        video_info = self.__scan_resolutions(video_paths, context)
        if not video_info:
            return self.__handle_failed_analysis(video_paths, context)

        upscaling_pct = self.__analyze_and_report(video_info, context)
        self.__save_results_to_json(video_info, upscaling_pct, context)

        context.mark_step_completed(self.name, 'all')
        return ResolutionAnalysisResult(
            total_files=len(video_info), upscaling_percentage=upscaling_pct,
        )

    def __log_analysis_header(self, context: ExecutionContext) -> None:
        context.logger.info('=' * 80)
        context.logger.info('RESOLUTION ANALYSIS - Checking source video resolutions')
        context.logger.info('=' * 80)

    def __handle_missing_videos(self, context: ExecutionContext) -> ResolutionAnalysisResult:
        context.logger.warning('No video files found - skipping resolution analysis')
        context.mark_step_completed(self.name, 'all')
        return ResolutionAnalysisResult(total_files=0, upscaling_percentage=0.0)

    def __handle_failed_analysis(
            self, video_paths: List[Path], context: ExecutionContext,
    ) -> ResolutionAnalysisResult:
        context.logger.warning('Failed to analyze videos - skipping')
        context.mark_step_completed(self.name, 'all')
        return ResolutionAnalysisResult(total_files=len(video_paths), upscaling_percentage=0.0)

    def __analyze_and_report(
            self, video_info: List[Dict[str, Any]], context: ExecutionContext,
    ) -> float:
        resolution_counts = Counter((v['width'], v['height']) for v in video_info)
        total_episodes = len(video_info)

        target_width = self.config.resolution.width
        target_height = self.config.resolution.height
        target_pixels = target_width * target_height

        upscaling_count = sum(
            1 for v in video_info
            if (v['width'] * v['height']) < target_pixels
        )
        upscaling_pct = (upscaling_count / total_episodes) * 100 if total_episodes > 0 else 0

        needs_deinterlace_count = sum(1 for v in video_info if v['needs_deinterlace'])
        progressive_count = sum(1 for v in video_info if not v['needs_deinterlace'])
        metadata_mismatch_count = sum(1 for v in video_info if v['metadata_match'] != 'match')

        self.__log_resolution_distribution(
            context, resolution_counts, total_episodes, target_width, target_height,
        )
        self.__log_upscaling_warnings(context, upscaling_pct)
        self.__log_interlacing_analysis(
            context, progressive_count, needs_deinterlace_count, total_episodes,
        )
        self.__log_metadata_warnings(context, metadata_mismatch_count)

        context.logger.info('=' * 80)
        return upscaling_pct

    def __log_resolution_distribution(
            self,
            context: ExecutionContext,
            resolution_counts: Counter,
            total_episodes: int,
            target_width: int,
            target_height: int,
    ) -> None:
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

    def __log_upscaling_warnings(self, context: ExecutionContext, upscaling_pct: float) -> None:
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

    def __log_interlacing_analysis(
            self,
            context: ExecutionContext,
            progressive_count: int,
            needs_deinterlace_count: int,
            total_episodes: int,
    ) -> None:
        context.logger.info('')
        context.logger.info('Interlacing Analysis (based on idet, not metadata):')
        context.logger.info('-' * 60)
        context.logger.info(
            f'  Progressive: {progressive_count} episodes '
            f'({(progressive_count / total_episodes) * 100:.1f}%)',
        )
        context.logger.info(
            f'  Interlaced (needs deinterlace): {needs_deinterlace_count} episodes '
            f'({(needs_deinterlace_count / total_episodes) * 100:.1f}%)',
        )

    def __log_metadata_warnings(self, context: ExecutionContext, mismatch_count: int) -> None:
        if mismatch_count > 0:
            context.logger.warning('')
            context.logger.warning(
                f'⚠ WARNING: {mismatch_count} episodes have INCORRECT field_order metadata!',
            )
            context.logger.warning(
                '⚠ Using idet analysis instead of metadata for deinterlacing decisions.',
            )

    def __save_results_to_json(
            self,
            video_info: List[Dict[str, Any]],
            upscaling_pct: float,
            context: ExecutionContext,
    ) -> None:
        output_file = self.__resolve_output_file(context)

        resolution_counts = Counter((v['width'], v['height']) for v in video_info)
        total_episodes = len(video_info)

        target_width = self.config.resolution.width
        target_height = self.config.resolution.height
        target_pixels = target_width * target_height

        upscaling_count = sum(
            1 for v in video_info
            if (v['width'] * v['height']) < target_pixels
        )
        needs_deinterlace_count = sum(1 for v in video_info if v['needs_deinterlace'])
        progressive_count = sum(1 for v in video_info if not v['needs_deinterlace'])
        metadata_mismatch_count = sum(1 for v in video_info if v['metadata_match'] != 'match')

        result = self.__build_analysis_payload(
            context,
            video_info,
            resolution_counts,
            total_episodes,
            target_width,
            target_height,
            target_pixels,
            upscaling_count,
            upscaling_pct,
            progressive_count,
            needs_deinterlace_count,
            metadata_mismatch_count,
        )

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        context.logger.info(f'Resolution analysis saved to: {output_file}')

    def __build_analysis_payload(  # pylint: disable=too-many-arguments
            self,
            context: ExecutionContext,
            video_info: List[Dict[str, Any]],
            resolution_counts: Counter,
            total_episodes: int,
            target_width: int,
            target_height: int,
            target_pixels: int,
            upscaling_count: int,
            upscaling_pct: float,
            progressive_count: int,
            needs_deinterlace_count: int,
            metadata_mismatch_count: int,
    ) -> Dict[str, Any]:
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
                'filename': v['filename'],
                'width': v['width'],
                'height': v['height'],
                'label': self.__get_resolution_label(v['width'], v['height']),
                'needs_upscaling': (v['width'] * v['height']) < target_pixels,
                'field_order': v['field_order'],
                'needs_deinterlace': v['needs_deinterlace'],
                'metadata_match': v['metadata_match'],
                'idet_stats': v['idet_stats'],
            }
            for v in sorted(video_info, key=lambda x: x['filename'])
        ]

        return {
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
            'interlacing_analysis': {
                'progressive': {
                    'count': progressive_count,
                    'percentage': round((progressive_count / total_episodes) * 100, 1),
                },
                'interlaced': {
                    'count': needs_deinterlace_count,
                    'percentage': round((needs_deinterlace_count / total_episodes) * 100, 1),
                },
                'metadata_mismatches': {
                    'count': metadata_mismatch_count,
                    'percentage': round((metadata_mismatch_count / total_episodes) * 100, 1),
                },
            },
            'files': files_details,
        }

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
    ) -> List[Dict[str, Any]]:
        video_info = []

        for video_path in video_paths:
            try:
                probe_data = FFmpegWrapper.probe_video(video_path)
                width, height = FFmpegWrapper.get_resolution(probe_data)
                sar_num, sar_denom = FFmpegWrapper.get_sample_aspect_ratio(probe_data)
                field_order = FFmpegWrapper.get_field_order(probe_data)

                effective_width = int(width * sar_num / sar_denom)

                context.logger.info(
                    f'Analyzing interlacing for {video_path.name} '
                    f'(field_order={field_order}, analyzing full video)...',
                )
                has_interlacing, idet_stats = FFmpegWrapper.detect_interlacing(
                    video_path, analysis_time=None,
                )

                metadata_vs_reality = ResolutionAnalysisStep.__validate_field_order(
                    field_order, has_interlacing, idet_stats,
                )

                if metadata_vs_reality != 'match':
                    context.logger.warning(
                        f'⚠ {video_path.name}: field_order={field_order} but idet says {metadata_vs_reality}!',
                    )

                video_info.append({
                    'filename': video_path.name,
                    'width': effective_width,
                    'height': height,
                    'field_order': field_order,
                    'needs_deinterlace': has_interlacing,
                    'idet_stats': idet_stats,
                    'metadata_match': metadata_vs_reality,
                })

            except Exception as e:
                context.logger.warning(f'Failed to probe {video_path.name}: {e}')
                continue

        return video_info

    @staticmethod
    def __validate_field_order(
            field_order: str, has_interlacing: bool, idet_stats: Optional[Dict[str, int]],
    ) -> str:
        if not idet_stats:
            return 'unknown'

        metadata_says_progressive = field_order in {'progressive', 'unknown'}
        idet_says_progressive = not has_interlacing

        if metadata_says_progressive and idet_says_progressive:
            return 'match'
        if not metadata_says_progressive and not idet_says_progressive:
            return 'match'
        if metadata_says_progressive and not idet_says_progressive:
            return 'interlaced (metadata wrong)'
        return 'progressive (metadata wrong)'

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

    @staticmethod
    def __resolve_output_file(context: ExecutionContext) -> Path:
        output_base = PathService.get_output_base()
        output_dir = output_base / context.series_name
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir / 'resolution_analysis.json'
