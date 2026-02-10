import logging
from typing import List, Dict, Any, Optional


class MockElasticsearch:
    _segments: List[Dict[str, Any]] = []
    _call_log: List[Dict[str, Any]] = []

    @classmethod
    def reset(cls):
        cls._segments = []
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
        segment = {
            'text': text,
            'start_time': start,
            'end_time': end,
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
        season_filter: Optional[int] = None,
        episode_filter: Optional[int] = None,
        size: int = 1
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
        logger: logging.Logger,
        series_name: str
    ) -> Dict[str, int]:
        cls._call_log.append({
            'method': 'get_season_details_from_elastic',
            'series_name': series_name,
        })

        seasons = set()
        episodes = set()
        for segment in cls._segments:
            ep_info = segment.get('episode_info', {})
            seasons.add(ep_info.get('season', 1))
            episodes.add(ep_info.get('episode_number', 1))

        return {
            'seasons': max(seasons) if seasons else 1,
            'episodes': max(episodes) if episodes else 1,
        }

    @classmethod
    def get_call_log(cls) -> List[Dict[str, Any]]:
        return cls._call_log

    @classmethod
    def get_call_count(cls, method_name: str) -> int:
        return sum(1 for call in cls._call_log if call['method'] == method_name)
