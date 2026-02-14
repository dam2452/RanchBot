import logging
from typing import (
    Any,
    Dict,
    List,
    Optional,
)


class MockElasticsearch:
    _segments: List[Dict[str, Any]] = []
    _video_paths: Dict[tuple, str] = {}
    _call_log: List[Dict[str, Any]] = []

    @classmethod
    def reset(cls):
        cls._segments = []
        cls._video_paths = {}
        cls._call_log = []

    @classmethod
    def add_segment(
        cls,
        text: str,
        start: float,
        end: float,
        video_path: str,
        quote_keywords: Optional[List[str]] = None,
        season: int = 1,
        episode_number: int = 1,
        episode_title: str = "Test Episode",
    ):
        segment_id = len(cls._segments) + 1
        segment = {
            'id': segment_id,
            'text': text,
            'start_time': start,
            'end_time': end,
            'start': start,
            'end': end,
            'video_path': video_path,
            'episode_info': {
                'season': season,
                'episode_number': episode_number,
                'title': episode_title,
            },
            '_quote_keywords': quote_keywords or [],
        }
        cls._segments.append(segment)

    @classmethod
    def set_segments(cls, segments: List[Dict[str, Any]]):
        cls._segments = segments

    @classmethod
    async def find_segment_by_quote(
        cls,
        quote: str,
        logger: logging.Logger,
        series_name: str,
        _season_filter: Optional[int] = None,
        _episode_filter: Optional[int] = None,
        size: int = 1,
    ) -> List[Dict[str, Any]]:
        cls._call_log.append({
            'method': 'find_segment_by_quote',
            'quote': quote,
            'series_name': series_name,
            'size': size,
        })

        query_text = quote.lower()

        matching_segments = []
        for segment in cls._segments:
            segment_text = segment['text'].lower()
            keywords = segment.get('_quote_keywords', [])

            if query_text in segment_text or any(kw.lower() in query_text for kw in keywords):
                matching_segments.append(segment)

            if len(matching_segments) >= size:
                break

        logger.info(f"MockElasticsearch: Found {len(matching_segments)} segments for query '{query_text}'")
        return matching_segments

    @classmethod
    async def get_season_details_from_elastic(
        cls,
        _logger: logging.Logger,
        series_name: str,
    ) -> Dict[str, int]:
        cls._call_log.append({
            'method': 'get_season_details_from_elastic',
            'series_name': series_name,
        })

        season_episodes = {}
        for segment in cls._segments:
            ep_info = segment.get('episode_info', {})
            season = ep_info.get('season', 1)
            episode_num = ep_info.get('episode_number', 1)
            season_key = str(season)
            if season_key not in season_episodes:
                season_episodes[season_key] = set()
            season_episodes[season_key].add(episode_num)

        if not season_episodes:
            return {'1': 10}

        return {season_key: len(episodes) for season_key, episodes in season_episodes.items()}

    @classmethod
    def get_call_log(cls) -> List[Dict[str, Any]]:
        return cls._call_log

    @classmethod
    def get_call_count(cls, method_name: str) -> int:
        return sum(1 for call in cls._call_log if call['method'] == method_name)

    @classmethod
    def add_video_path(cls, season: int, episode: int, video_path: str):
        cls._video_paths[(season, episode)] = video_path

    @classmethod
    async def find_video_path_by_episode(cls, season: int, episode: int, _logger: logging.Logger) -> Optional[str]:
        cls._call_log.append({
            'method': 'find_video_path_by_episode',
            'season': season,
            'episode': episode,
        })
        return cls._video_paths.get((season, episode))

    @classmethod
    async def find_episodes_by_season(cls, season: int, _logger: logging.Logger, _index: str = None) -> List[Dict[str, Any]]:
        cls._call_log.append({
            'method': 'find_episodes_by_season',
            'season': season,
        })
        episodes = []
        for segment in cls._segments:
            ep_info = segment.get('episode_info', {})
            if ep_info.get('season') == season:
                episode_data = {
                    'episode_number': ep_info.get('episode_number'),
                    'title': ep_info.get('title', 'Test Episode'),
                }
                if episode_data not in episodes:
                    episodes.append(episode_data)
        return episodes

    @classmethod
    async def find_segment_with_context(cls, quote: str, logger: logging.Logger, series_name: str, context_size: int = 15):
        cls._call_log.append({
            'method': 'find_segment_with_context',
            'quote': quote,
            'context_size': context_size,
        })
        segments = await cls.find_segment_by_quote(quote, logger, series_name, size=1)
        if not segments:
            return None

        target_segment = segments[0]
        return {
            'target': target_segment,
            'context': [target_segment],
            'overall_start_time': target_segment.get('start_time', target_segment.get('start', 0.0)),
            'overall_end_time': target_segment.get('end_time', target_segment.get('end', 0.0)),
        }
