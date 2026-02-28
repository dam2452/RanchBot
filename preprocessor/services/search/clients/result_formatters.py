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
        return f'{int(seconds // 60)}m {seconds % 60:.1f}s'

    @staticmethod
    def print_results(result: Dict[str, Any], result_type: str = 'text') -> None:
        hits_data = result[ElasticsearchKeys.HITS]
        total = hits_data[ElasticsearchKeys.TOTAL][ElasticsearchAggregationKeys.VALUE]
        hits = hits_data[ElasticsearchKeys.HITS]

        click.echo(f'\nResults found: {total}')
        click.echo('=' * 80)

        for i, hit in enumerate(hits, 1):
            source = hit[ElasticsearchKeys.SOURCE]
            meta = source[EpisodeMetadataKeys.EPISODE_METADATA]

            click.echo(f'\n[{i}] Score: {hit[ElasticsearchKeys.SCORE]:.2f}')
            click.echo(f"Episode: S{meta['season']:02d}E{meta['episode_number']:02d} - {meta.get('title', 'N/A')}")

            ResultFormatter.__print_specific_content(source, result_type)
            click.echo(f"Video: {source['video_path']}")

    @staticmethod
    def __print_specific_content(source: Dict[str, Any], r_type: str) -> None:
        scene_ctx = ResultFormatter.__get_scene_ctx(source.get('scene_info'))

        if r_type == 'text':
            click.echo(
                f"Time: {ResultFormatter.format_timestamp(source['start_time'])} - {ResultFormatter.format_timestamp(source['end_time'])}{scene_ctx}",
            )
            click.echo(f"Speaker: {source.get('speaker', 'N/A')}\nText: {source['text']}")
        elif r_type == 'text_semantic':
            click.echo(f"Range: {source['segment_range']}{scene_ctx}\nText: {source['text']}")
        else:
            ts = ResultFormatter.format_timestamp(source['timestamp'])
            click.echo(f"Frame: {source['frame_number']} @ {ts}{scene_ctx}")
            if source.get('character_appearances'):
                click.echo(f"Characters: {ResultFormatter.__fmt_chars(source['character_appearances'])}")

    @staticmethod
    def __get_scene_ctx(info: Optional[Dict[str, Any]]) -> str:
        if not info:
            return ''
        return f" [Scene {info.get('scene_number')}: {ResultFormatter.format_timestamp(info.get('scene_start_time', 0))}]"

    @staticmethod
    def __fmt_chars(appearances: list) -> str:
        return ', '.join([f"{c['name']} ({c['emotion']['label']})" for c in appearances if 'emotion' in c])
