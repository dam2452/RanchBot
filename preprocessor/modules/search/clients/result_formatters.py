from typing import (
    Any,
    Dict,
    Optional,
)

import click

from preprocessor.config.types import (
    ElasticsearchAggregationKeys,
    ElasticsearchKeys,
    EpisodeMetadataKeys,
)


class ResultFormatter:

    @staticmethod
    def format_timestamp(seconds: float) -> str:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f'{minutes}m {secs:.1f}s'

    @staticmethod
    def _format_scene_context(scene_info: Optional[Dict[str, Any]]) -> str:
        if not scene_info:
            return ''
        start = ResultFormatter.format_timestamp(scene_info.get('scene_start_time', 0))
        end = ResultFormatter.format_timestamp(scene_info.get('scene_end_time', 0))
        return f" [Scene {scene_info.get('scene_number', '?')}: {start} - {end}]"

    @staticmethod
    def __format_character_appearances(appearances: list) -> str:
        """Format character appearances with emotions."""
        chars_strs = []
        for char in appearances:
            char_str = char.get('name', 'Unknown')
            if char.get('emotion'):
                emotion_label = char['emotion'].get('label', '?')
                emotion_conf = char['emotion'].get('confidence', 0)
                char_str += f' ({emotion_label} {emotion_conf:.2f})'
            chars_strs.append(char_str)
        return ', '.join(chars_strs)

    @staticmethod
    def __format_detected_objects(objects: list) -> str:
        """Format detected objects list."""
        return ', '.join([f"{obj['class']}:{obj['count']}" for obj in objects])

    @staticmethod
    def __print_text_result(source: Dict[str, Any], scene_ctx: str) -> None:
        """Print text search result."""
        click.echo(f"Segment ID: {source.get('segment_id', 'N/A')}")
        start_time = ResultFormatter.format_timestamp(source['start_time'])
        end_time = ResultFormatter.format_timestamp(source['end_time'])
        click.echo(f'Time: {start_time} - {end_time}{scene_ctx}')
        click.echo(f"Speaker: {source.get('speaker', 'N/A')}")
        click.echo(f"Text: {source['text']}")

    @staticmethod
    def __print_video_result(source: Dict[str, Any], scene_ctx: str) -> None:
        """Print video/frame search result."""
        timestamp = ResultFormatter.format_timestamp(source['timestamp'])
        click.echo(f"Frame: {source['frame_number']} @ {timestamp}{scene_ctx}")
        if 'frame_type' in source:
            click.echo(f"Type: {source['frame_type']}")
        if 'scene_number' in source:
            click.echo(f"Scene number: {source['scene_number']}")
        if 'perceptual_hash' in source:
            click.echo(f"Hash: {source['perceptual_hash']}")
        if source.get('character_appearances'):
            chars = ResultFormatter.__format_character_appearances(source['character_appearances'])
            click.echo(f"Characters: {chars}")
        if source.get('detected_objects'):
            objects = ResultFormatter.__format_detected_objects(source['detected_objects'])
            click.echo(f'Objects: {objects}')

    @staticmethod
    def print_results(result: Dict[str, Any], result_type: str='text') -> None:
        total = result[ElasticsearchKeys.HITS][ElasticsearchKeys.TOTAL][ElasticsearchAggregationKeys.VALUE]
        hits = result[ElasticsearchKeys.HITS][ElasticsearchKeys.HITS]
        click.echo(f'\nZnaleziono: {total} wynikow')
        click.echo('=' * 80)
        for i, hit in enumerate(hits, 1):
            source = hit[ElasticsearchKeys.SOURCE]
            score = hit[ElasticsearchKeys.SCORE]
            meta = source[EpisodeMetadataKeys.EPISODE_METADATA]
            scene_ctx = ResultFormatter._format_scene_context(source.get('scene_info'))
            click.echo(f'\n[{i}] Score: {score:.2f}')
            season_code = 'S00' if meta['season'] == 0 else f"S{meta['season']:02d}"
            click.echo(f"Episode: {season_code}E{meta['episode_number']:02d} - {meta.get('title', 'N/A')}")
            if result_type == 'text':
                ResultFormatter.__print_text_result(source, scene_ctx)
            elif result_type == 'text_semantic':
                click.echo(f"Segments: {source['segment_range'][0]}-{source['segment_range'][1]}{scene_ctx}")
                click.echo(f"Embedding ID: {source.get('embedding_id', 'N/A')}")
                click.echo(f"Text: {source['text']}")
            elif result_type == 'episode_name':
                click.echo(f"Episode Title: {source.get('title', 'N/A')}")
            else:
                ResultFormatter.__print_video_result(source, scene_ctx)
            click.echo(f"Path: {source['video_path']}")
