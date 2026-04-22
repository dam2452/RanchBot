import asyncio
import bisect
import logging
import math
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    cast,
)

from elasticsearch import RequestError

from bot.responses.not_sending_videos.emotions_handler_responses import map_emotion_to_en
from bot.search.infra.elastic_search_manager import ElasticSearchManager
from bot.search.video_frames.frames_finder import _build_index
from bot.search.video_frames.object_finder import _OPERATORS
from bot.types import (
    ObjectFilterSpec,
    SearchFilter,
    SegmentWithScore,
)
from bot.utils.constants import (
    ActorKeys,
    DetectedObjectKeys,
    ElasticsearchKeys,
    ElasticsearchQueryKeys,
    EmotionKeys,
    EpisodeMetadataKeys,
    SegmentKeys,
    VideoFrameKeys,
)
from bot.utils.log import log_system_message


class FilterApplicator:
    __PAGE_SIZE = 1000

    @staticmethod
    def _extract_field_value(hit: Dict[str, Any], field: str, default: Any = None) -> Any:
        fields = hit.get("fields", {})
        if field in fields:
            values = fields.get(field, [])
            return values[0] if values else default
        source = hit.get(ElasticsearchKeys.SOURCE, {})
        return source.get(field, default)

    @staticmethod
    def _build_episode_pairs_filter(
        episode_keys: Set[Tuple[Optional[int], Optional[int]]],
    ) -> Optional[Dict[str, Any]]:
        valid_keys = [(season, episode) for season, episode in episode_keys if season is not None and episode is not None]
        if not valid_keys:
            return None
        return {
            ElasticsearchQueryKeys.BOOL: {
                ElasticsearchQueryKeys.SHOULD: [
                    {
                        ElasticsearchQueryKeys.BOOL: {
                            ElasticsearchQueryKeys.FILTER: [
                                {ElasticsearchQueryKeys.TERM: {EpisodeMetadataKeys.SEASON_FIELD: season}},
                                {ElasticsearchQueryKeys.TERM: {EpisodeMetadataKeys.EPISODE_NUMBER_FIELD: episode}},
                            ],
                        },
                    }
                    for season, episode in valid_keys
                ],
                ElasticsearchQueryKeys.MINIMUM_SHOULD_MATCH: 1,
            },
        }

    @staticmethod
    async def apply_to_text_segments(
        segments: List[SegmentWithScore],
        search_filter: SearchFilter,
        series_name: str,
        logger: logging.Logger,
    ) -> List[SegmentWithScore]:
        character_groups = search_filter.get("character_groups", [])
        object_groups = search_filter.get("object_groups", [])
        emotions = search_filter.get("emotions", [])

        if not character_groups and not object_groups and not emotions:
            return segments

        episode_keys = {
            (
                cast(Dict[str, Any], seg.get(EpisodeMetadataKeys.EPISODE_METADATA, {})).get(EpisodeMetadataKeys.SEASON),
                cast(Dict[str, Any], seg.get(EpisodeMetadataKeys.EPISODE_METADATA, {})).get(EpisodeMetadataKeys.EPISODE_NUMBER),
            )
            for seg in segments
        }

        char_tasks = []
        for char_group in character_groups:
            char_tasks.append(FilterApplicator._get_character_frame_keys(char_group, episode_keys, series_name, logger))
        if emotions:
            char_tasks.append(FilterApplicator._get_emotion_frame_keys(emotions, episode_keys, series_name, logger))
        for obj_group in object_groups:
            char_tasks.append(FilterApplicator._get_object_frame_keys(obj_group, episode_keys, series_name, logger))

        frame_key_sets = list(await asyncio.gather(*char_tasks))

        hit_episode_keys: Set[Tuple[Optional[int], Optional[int]]] = {
            (fk_season, fk_episode)
            for frame_keys in frame_key_sets
            for fk_season, fk_episode, _ in frame_keys
            if fk_season is not None and fk_episode is not None
        }
        all_timestamps = await FilterApplicator._get_all_frame_timestamps(hit_episode_keys, series_name, logger)

        filtered = [
            seg for seg in segments
            if FilterApplicator._segment_passes_all(seg, frame_key_sets, all_timestamps)
        ]
        await log_system_message(
            logging.INFO,
            f"FilterApplicator: {len(segments)} → {len(filtered)} segments after video-frame filters.",
            logger,
        )
        return filtered

    @staticmethod
    def _segment_passes_all(
        segment: SegmentWithScore,
        frame_key_sets: List[Set[Tuple[Optional[int], Optional[int], float]]],
        all_timestamps: Dict[Tuple[Optional[int], Optional[int]], List[float]],
    ) -> bool:
        meta = cast(Dict[str, Any], segment.get(EpisodeMetadataKeys.EPISODE_METADATA, {}))
        season = meta.get(EpisodeMetadataKeys.SEASON)
        episode = meta.get(EpisodeMetadataKeys.EPISODE_NUMBER)
        start = float(segment.get(SegmentKeys.START_TIME, 0.0))
        end = float(segment.get(SegmentKeys.END_TIME, 0.0))
        ep_timestamps = all_timestamps.get((season, episode), [])

        def __scene_overlaps(frame_keys: Set[Tuple[Optional[int], Optional[int], float]]) -> bool:
            for fk_season, fk_episode, ts in frame_keys:
                if fk_season != season or fk_episode != episode:
                    continue
                idx = bisect.bisect_right(ep_timestamps, ts)
                next_ts = ep_timestamps[idx] if idx < len(ep_timestamps) else math.inf
                if ts <= end and next_ts >= start:
                    return True
            return False

        return all(__scene_overlaps(fk) for fk in frame_key_sets)

    @staticmethod
    async def _get_character_frame_keys(
        char_names: List[str],
        episode_keys: Set[Tuple[Optional[int], Optional[int]]],
        series_name: str,
        logger: logging.Logger,
    ) -> Set[Tuple[Optional[int], Optional[int], float]]:
        es = await ElasticSearchManager.connect_to_elasticsearch(logger)
        season_list = list({k[0] for k in episode_keys if k[0] is not None})
        episode_pairs_filter = FilterApplicator._build_episode_pairs_filter(episode_keys)
        should_clauses = [
            {
                ElasticsearchQueryKeys.NESTED: {
                    ElasticsearchQueryKeys.PATH: ActorKeys.ACTORS,
                    ElasticsearchQueryKeys.QUERY: {
                        ElasticsearchQueryKeys.TERM: {
                            f"{ActorKeys.ACTORS}.{ActorKeys.NAME}": {
                                ElasticsearchQueryKeys.VALUE: name,
                                ElasticsearchQueryKeys.CASE_INSENSITIVE: True,
                            },
                        },
                    },
                },
            }
            for name in char_names
        ]
        filter_clauses = [
            {
                ElasticsearchQueryKeys.BOOL: {
                    ElasticsearchQueryKeys.SHOULD: should_clauses,
                    ElasticsearchQueryKeys.MINIMUM_SHOULD_MATCH: 1,
                },
            },
        ]
        if season_list:
            filter_clauses.append({ElasticsearchQueryKeys.TERMS: {EpisodeMetadataKeys.SEASON_FIELD: season_list}})
        if episode_pairs_filter:
            filter_clauses.append(episode_pairs_filter)

        query = {
            ElasticsearchQueryKeys.QUERY: {
                ElasticsearchQueryKeys.BOOL: {
                    ElasticsearchQueryKeys.FILTER: filter_clauses,
                },
            },
            ElasticsearchQueryKeys.SOURCE: [
                EpisodeMetadataKeys.EPISODE_METADATA,
                VideoFrameKeys.TIMESTAMP,
            ],
        }
        hits = await ElasticSearchManager.search_all_hits(
            es,
            _build_index(series_name),
            query,
            page_size=FilterApplicator.__PAGE_SIZE,
        )
        return FilterApplicator._hits_to_frame_keys(hits)

    @staticmethod
    async def _get_emotion_frame_keys(
        emotions: List[str],
        episode_keys: Set[Tuple[Optional[int], Optional[int]]],
        series_name: str,
        logger: logging.Logger,
    ) -> Set[Tuple[Optional[int], Optional[int], float]]:
        emotion_labels_en = [en for e in emotions for en in (map_emotion_to_en(e),) if en]
        if not emotion_labels_en:
            return set()

        es = await ElasticSearchManager.connect_to_elasticsearch(logger)
        season_list = list({k[0] for k in episode_keys if k[0] is not None})
        episode_pairs_filter = FilterApplicator._build_episode_pairs_filter(episode_keys)
        should_clauses = [
            {
                ElasticsearchQueryKeys.NESTED: {
                    ElasticsearchQueryKeys.PATH: ActorKeys.ACTORS,
                    ElasticsearchQueryKeys.QUERY: {
                        ElasticsearchQueryKeys.TERM: {
                            f"{ActorKeys.ACTORS}.{ActorKeys.EMOTION}.{EmotionKeys.LABEL}": label,
                        },
                    },
                },
            }
            for label in emotion_labels_en
        ]
        filter_clauses = [
            {
                ElasticsearchQueryKeys.BOOL: {
                    ElasticsearchQueryKeys.SHOULD: should_clauses,
                    ElasticsearchQueryKeys.MINIMUM_SHOULD_MATCH: 1,
                },
            },
        ]
        if season_list:
            filter_clauses.append({ElasticsearchQueryKeys.TERMS: {EpisodeMetadataKeys.SEASON_FIELD: season_list}})
        if episode_pairs_filter:
            filter_clauses.append(episode_pairs_filter)

        query = {
            ElasticsearchQueryKeys.QUERY: {
                ElasticsearchQueryKeys.BOOL: {ElasticsearchQueryKeys.FILTER: filter_clauses},
            },
            ElasticsearchQueryKeys.SOURCE: [
                EpisodeMetadataKeys.EPISODE_METADATA,
                VideoFrameKeys.TIMESTAMP,
            ],
        }
        hits = await ElasticSearchManager.search_all_hits(
            es,
            _build_index(series_name),
            query,
            page_size=FilterApplicator.__PAGE_SIZE,
        )
        return FilterApplicator._hits_to_frame_keys(hits)

    @staticmethod
    async def _get_object_frame_keys(
        obj_group: List[ObjectFilterSpec],
        episode_keys: Set[Tuple[Optional[int], Optional[int]]],
        series_name: str,
        logger: logging.Logger,
    ) -> Set[Tuple[Optional[int], Optional[int], float]]:
        es = await ElasticSearchManager.connect_to_elasticsearch(logger)
        season_list = list({k[0] for k in episode_keys if k[0] is not None})
        episode_pairs_filter = FilterApplicator._build_episode_pairs_filter(episode_keys)

        should_clauses = [
            {
                ElasticsearchQueryKeys.NESTED: {
                    ElasticsearchQueryKeys.PATH: VideoFrameKeys.DETECTED_OBJECTS,
                    ElasticsearchQueryKeys.QUERY: {
                        ElasticsearchQueryKeys.TERM: {
                            DetectedObjectKeys.OBJECT_CLASS_FIELD: spec["name"],
                        },
                    },
                },
            }
            for spec in obj_group
        ]
        filter_clauses = [
            {
                ElasticsearchQueryKeys.BOOL: {
                    ElasticsearchQueryKeys.SHOULD: should_clauses,
                    ElasticsearchQueryKeys.MINIMUM_SHOULD_MATCH: 1,
                },
            },
        ]
        if season_list:
            filter_clauses.append({ElasticsearchQueryKeys.TERMS: {EpisodeMetadataKeys.SEASON_FIELD: season_list}})
        if episode_pairs_filter:
            filter_clauses.append(episode_pairs_filter)

        query = {
            ElasticsearchQueryKeys.QUERY: {
                ElasticsearchQueryKeys.BOOL: {ElasticsearchQueryKeys.FILTER: filter_clauses},
            },
            ElasticsearchQueryKeys.SOURCE: [
                EpisodeMetadataKeys.EPISODE_METADATA,
                VideoFrameKeys.TIMESTAMP,
                VideoFrameKeys.DETECTED_OBJECTS,
            ],
        }
        hits = await ElasticSearchManager.search_all_hits(
            es,
            _build_index(series_name),
            query,
            page_size=FilterApplicator.__PAGE_SIZE,
        )

        frame_keys = set()
        for hit in hits:
            src = hit.get(ElasticsearchKeys.SOURCE, {})
            meta = src.get(EpisodeMetadataKeys.EPISODE_METADATA, {})
            season = meta.get(EpisodeMetadataKeys.SEASON)
            episode = meta.get(EpisodeMetadataKeys.EPISODE_NUMBER)
            timestamp = float(src.get(VideoFrameKeys.TIMESTAMP, 0.0))
            detected = src.get(VideoFrameKeys.DETECTED_OBJECTS, [])

            if FilterApplicator.__frame_passes_object_group(detected, obj_group):
                frame_keys.add((season, episode, timestamp))

        return frame_keys

    @staticmethod
    async def _get_all_frame_timestamps(
        episode_keys: Set[Tuple[Optional[int], Optional[int]]],
        series_name: str,
        logger: logging.Logger,
    ) -> Dict[Tuple[Optional[int], Optional[int]], List[float]]:
        es = await ElasticSearchManager.connect_to_elasticsearch(logger)
        valid_keys = [(s, e) for s, e in episode_keys if s is not None and e is not None]
        episode_should = [
            {
                ElasticsearchQueryKeys.BOOL: {
                    ElasticsearchQueryKeys.FILTER: [
                        {ElasticsearchQueryKeys.TERM: {EpisodeMetadataKeys.SEASON_FIELD: s}},
                        {ElasticsearchQueryKeys.TERM: {EpisodeMetadataKeys.EPISODE_NUMBER_FIELD: e}},
                    ],
                },
            }
            for s, e in valid_keys
        ]
        if not episode_should:
            return {}
        query = {
            ElasticsearchQueryKeys.QUERY: {
                ElasticsearchQueryKeys.BOOL: {
                    ElasticsearchQueryKeys.FILTER: [
                        {
                            ElasticsearchQueryKeys.BOOL: {
                                ElasticsearchQueryKeys.SHOULD: episode_should,
                                ElasticsearchQueryKeys.MINIMUM_SHOULD_MATCH: 1,
                            },
                        },
                    ],
                },
            },
            ElasticsearchQueryKeys.SOURCE: False,
            "docvalue_fields": [
                EpisodeMetadataKeys.SEASON_FIELD,
                EpisodeMetadataKeys.EPISODE_NUMBER_FIELD,
                VideoFrameKeys.TIMESTAMP,
            ],
        }
        try:
            hits = await ElasticSearchManager.search_all_hits(
                es,
                _build_index(series_name),
                query,
                page_size=FilterApplicator.__PAGE_SIZE,
            )
        except RequestError:
            return {}
        result: Dict[Tuple[Optional[int], Optional[int]], List[float]] = {}
        for hit in hits:
            season = FilterApplicator._extract_field_value(hit, EpisodeMetadataKeys.SEASON_FIELD)
            episode_number = FilterApplicator._extract_field_value(hit, EpisodeMetadataKeys.EPISODE_NUMBER_FIELD)
            timestamp = FilterApplicator._extract_field_value(hit, VideoFrameKeys.TIMESTAMP, 0.0)
            key = (season, episode_number)
            result.setdefault(key, []).append(float(timestamp))
        for timestamps in result.values():
            timestamps.sort()
        await log_system_message(
            logging.INFO,
            f"FilterApplicator: loaded all-frame timestamps for {len(result)} episodes.",
            logger,
        )
        return result

    @staticmethod
    def __frame_passes_object_group(
        detected: List[Dict[str, Any]],
        obj_group: List[ObjectFilterSpec],
    ) -> bool:
        for spec in obj_group:
            obj_name = spec["name"]
            obj_op = spec.get("operator")
            obj_val = spec.get("value")
            count = next(
                (
                    int(o.get(DetectedObjectKeys.COUNT, 0)) for o in detected
                    if o.get(DetectedObjectKeys.CLASS, "").lower() == obj_name.lower()
                ),
                0,
            )
            if count == 0:
                continue
            if obj_op is None or _OPERATORS.get(obj_op, lambda c, v: False)(count, obj_val):
                return True
        return False

    @staticmethod
    def _hits_to_frame_keys(hits: List[Dict[str, Any]]) -> Set[Tuple[Optional[int], Optional[int], float]]:
        keys = set()
        for hit in hits:
            src = hit.get(ElasticsearchKeys.SOURCE, {})
            meta = src.get(EpisodeMetadataKeys.EPISODE_METADATA, {})
            season = meta.get(EpisodeMetadataKeys.SEASON)
            episode = meta.get(EpisodeMetadataKeys.EPISODE_NUMBER)
            if season is None:
                season = FilterApplicator._extract_field_value(hit, EpisodeMetadataKeys.SEASON_FIELD)
            if episode is None:
                episode = FilterApplicator._extract_field_value(hit, EpisodeMetadataKeys.EPISODE_NUMBER_FIELD)
            timestamp = src.get(VideoFrameKeys.TIMESTAMP)
            if timestamp is None:
                timestamp = FilterApplicator._extract_field_value(hit, VideoFrameKeys.TIMESTAMP, 0.0)
            keys.add((
                season,
                episode,
                float(timestamp),
            ))
        return keys

    @staticmethod
    def build_es_season_episode_clauses(search_filter: SearchFilter) -> List[Dict[str, Any]]:
        clauses: List[Dict[str, Any]] = []
        seasons = search_filter.get("seasons")
        if seasons:
            clauses.append({
                ElasticsearchQueryKeys.TERMS: {
                    f"{EpisodeMetadataKeys.EPISODE_METADATA}.{EpisodeMetadataKeys.SEASON}": seasons,
                },
            })
        episodes = search_filter.get("episodes")
        if episodes:
            episode_should: List[Dict[str, Any]] = []
            for ep in episodes:
                must_parts: List[Dict[str, Any]] = [
                    {
                        ElasticsearchQueryKeys.TERM: {
                            f"{EpisodeMetadataKeys.EPISODE_METADATA}.{EpisodeMetadataKeys.EPISODE_NUMBER}": ep["episode"],
                        },
                    },
                ]
                if ep.get("season") is not None:
                    must_parts.append({
                        ElasticsearchQueryKeys.TERM: {
                            f"{EpisodeMetadataKeys.EPISODE_METADATA}.{EpisodeMetadataKeys.SEASON}": ep["season"],
                        },
                    })
                episode_should.append({
                    ElasticsearchQueryKeys.BOOL: {ElasticsearchQueryKeys.FILTER: must_parts},
                })
            clauses.append({
                ElasticsearchQueryKeys.BOOL: {
                    ElasticsearchQueryKeys.SHOULD: episode_should,
                    ElasticsearchQueryKeys.MINIMUM_SHOULD_MATCH: 1,
                },
            })
        return clauses

    @staticmethod
    def get_seasons_list(search_filter: SearchFilter) -> Optional[List[int]]:
        return search_filter.get("seasons")
