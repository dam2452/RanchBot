import asyncio
import logging
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
)

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
                seg.get(EpisodeMetadataKeys.EPISODE_METADATA, {}).get(EpisodeMetadataKeys.SEASON),
                seg.get(EpisodeMetadataKeys.EPISODE_METADATA, {}).get(EpisodeMetadataKeys.EPISODE_NUMBER),
            )
            for seg in segments
        }

        tasks = []
        for char_group in character_groups:
            tasks.append(FilterApplicator._get_character_frame_keys(char_group, episode_keys, series_name, logger))
        if emotions:
            tasks.append(FilterApplicator._get_emotion_frame_keys(emotions, episode_keys, series_name, logger))
        for obj_group in object_groups:
            tasks.append(FilterApplicator._get_object_frame_keys(obj_group, episode_keys, series_name, logger))

        frame_key_sets = await asyncio.gather(*tasks)

        filtered = [
            seg for seg in segments
            if FilterApplicator._segment_passes_all(seg, frame_key_sets)
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
    ) -> bool:
        meta = segment.get(EpisodeMetadataKeys.EPISODE_METADATA, {})
        season = meta.get(EpisodeMetadataKeys.SEASON)
        episode = meta.get(EpisodeMetadataKeys.EPISODE_NUMBER)
        start = segment.get(SegmentKeys.START_TIME, 0.0)
        end = segment.get(SegmentKeys.END_TIME, 0.0)
        return all(
            any(
                fk_season == season and fk_episode == episode and start <= fk_ts <= end
                for fk_season, fk_episode, fk_ts in frame_keys
                if fk_season == season and fk_episode == episode
            )
            for frame_keys in frame_key_sets
        )

    @staticmethod
    async def _get_character_frame_keys(
        char_names: List[str],
        episode_keys: Set[Tuple[Optional[int], Optional[int]]],
        series_name: str,
        logger: logging.Logger,
    ) -> Set[Tuple[Optional[int], Optional[int], float]]:
        es = await ElasticSearchManager.connect_to_elasticsearch(logger)
        season_list = list({k[0] for k in episode_keys if k[0] is not None})
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

        query = {
            ElasticsearchQueryKeys.QUERY: {
                ElasticsearchQueryKeys.BOOL: {
                    ElasticsearchQueryKeys.FILTER: filter_clauses,
                },
            },
            ElasticsearchQueryKeys.SOURCE: [
                EpisodeMetadataKeys.SEASON_FIELD,
                EpisodeMetadataKeys.EPISODE_NUMBER_FIELD,
                VideoFrameKeys.TIMESTAMP,
            ],
            ElasticsearchQueryKeys.SIZE: 10000,
        }
        resp = await es.search(index=_build_index(series_name), body=query)
        return FilterApplicator._hits_to_frame_keys(resp[ElasticsearchKeys.HITS][ElasticsearchKeys.HITS])

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

        query = {
            ElasticsearchQueryKeys.QUERY: {
                ElasticsearchQueryKeys.BOOL: {ElasticsearchQueryKeys.FILTER: filter_clauses},
            },
            ElasticsearchQueryKeys.SOURCE: [
                EpisodeMetadataKeys.SEASON_FIELD,
                EpisodeMetadataKeys.EPISODE_NUMBER_FIELD,
                VideoFrameKeys.TIMESTAMP,
            ],
            ElasticsearchQueryKeys.SIZE: 10000,
        }
        resp = await es.search(index=_build_index(series_name), body=query)
        return FilterApplicator._hits_to_frame_keys(resp[ElasticsearchKeys.HITS][ElasticsearchKeys.HITS])

    @staticmethod
    async def _get_object_frame_keys(
        obj_group: List[ObjectFilterSpec],
        episode_keys: Set[Tuple[Optional[int], Optional[int]]],
        series_name: str,
        logger: logging.Logger,
    ) -> Set[Tuple[Optional[int], Optional[int], float]]:
        es = await ElasticSearchManager.connect_to_elasticsearch(logger)
        season_list = list({k[0] for k in episode_keys if k[0] is not None})

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

        query = {
            ElasticsearchQueryKeys.QUERY: {
                ElasticsearchQueryKeys.BOOL: {ElasticsearchQueryKeys.FILTER: filter_clauses},
            },
            ElasticsearchQueryKeys.SOURCE: [
                EpisodeMetadataKeys.SEASON_FIELD,
                EpisodeMetadataKeys.EPISODE_NUMBER_FIELD,
                VideoFrameKeys.TIMESTAMP,
                VideoFrameKeys.DETECTED_OBJECTS,
            ],
            ElasticsearchQueryKeys.SIZE: 10000,
        }
        resp = await es.search(index=_build_index(series_name), body=query)
        hits = resp[ElasticsearchKeys.HITS][ElasticsearchKeys.HITS]

        frame_keys = set()
        for hit in hits:
            src = hit[ElasticsearchKeys.SOURCE]
            meta = src.get(EpisodeMetadataKeys.EPISODE_METADATA, {})
            season = meta.get(EpisodeMetadataKeys.SEASON)
            episode = meta.get(EpisodeMetadataKeys.EPISODE_NUMBER)
            timestamp = src.get(VideoFrameKeys.TIMESTAMP, 0.0)
            detected = src.get(VideoFrameKeys.DETECTED_OBJECTS, [])

            if FilterApplicator.__frame_passes_object_group(detected, obj_group):
                frame_keys.add((season, episode, timestamp))

        return frame_keys

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
            src = hit[ElasticsearchKeys.SOURCE]
            meta = src.get(EpisodeMetadataKeys.EPISODE_METADATA, {})
            keys.add((
                meta.get(EpisodeMetadataKeys.SEASON),
                meta.get(EpisodeMetadataKeys.EPISODE_NUMBER),
                src.get(VideoFrameKeys.TIMESTAMP, 0.0),
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
            episode_should = []
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
                    ElasticsearchQueryKeys.BOOL: {ElasticsearchQueryKeys.MUST: must_parts},
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
