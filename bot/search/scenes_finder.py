import logging
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from bot.responses.not_sending_videos.emotions_handler_responses import map_emotion_to_en
from bot.search.filter_applicator import _build_season_episode_clauses
from bot.search.infra.elastic_search_manager import build_fuzzy_with_boost_query
from bot.settings import settings
from bot.types import (
    SearchFilter,
    SegmentWithScore,
)
from bot.utils.constants import (
    ActorKeys,
    DetectedObjectKeys,
    ElasticsearchIndexSuffixes,
    ElasticsearchKeys,
    ElasticsearchQueryKeys,
    EmbeddingKeys,
    EmotionKeys,
    EpisodeMetadataKeys,
    SegmentKeys,
    VideoFrameKeys,
)
from bot.utils.log import log_system_message


class ScenesFinder:
    __FRAMES = "frames"
    __FRAMES_CHARACTERS = f"{__FRAMES}.{ActorKeys.ACTORS}"
    __FRAMES_OBJECTS = f"{__FRAMES}.{VideoFrameKeys.DETECTED_OBJECTS}"
    __CHAR_CONFIDENCE_FIELD = f"{__FRAMES}.{ActorKeys.ACTORS}.{ActorKeys.CONFIDENCE}"
    __EMOTION_CONFIDENCE_FIELD = (
        f"{__FRAMES}.{ActorKeys.ACTORS}.{ActorKeys.EMOTION}.{EmotionKeys.CONFIDENCE}"
    )
    __OBJECT_COUNT_FIELD = f"{__FRAMES}.{VideoFrameKeys.DETECTED_OBJECTS}.{DetectedObjectKeys.COUNT}"

    __SOURCE_FIELDS = [
        EpisodeMetadataKeys.EPISODE_METADATA,
        EmbeddingKeys.EPISODE_ID,
        SegmentKeys.SEGMENT_ID,
        "text",
        SegmentKeys.START_TIME,
        SegmentKeys.END_TIME,
        "speaker",
        SegmentKeys.VIDEO_PATH,
        "scene_info",
    ]

    @staticmethod
    def _attach_scores(hits: List[Dict[str, Any]]) -> List[SegmentWithScore]:
        results: List[SegmentWithScore] = []
        for hit in hits:
            source = hit[ElasticsearchKeys.SOURCE]
            source[ElasticsearchKeys.SCORE] = hit.get(ElasticsearchKeys.SCORE) or 0.0
            results.append(source)
        return results

    @staticmethod
    def _deduplicate_hits(segments: List[SegmentWithScore]) -> List[SegmentWithScore]:
        unique: List[SegmentWithScore] = []
        seen = set()
        for segment in segments:
            key = (
                segment.get(EpisodeMetadataKeys.EPISODE_METADATA, {}).get(EpisodeMetadataKeys.SEASON),
                segment.get(EpisodeMetadataKeys.EPISODE_METADATA, {}).get(EpisodeMetadataKeys.EPISODE_NUMBER),
                segment.get(SegmentKeys.START_TIME),
                segment.get(SegmentKeys.END_TIME),
            )
            if key in seen:
                continue
            seen.add(key)
            start_time = segment[SegmentKeys.START_TIME] - settings.EXTEND_BEFORE
            end_time = segment[SegmentKeys.END_TIME] + settings.EXTEND_AFTER
            if ScenesFinder._merge_overlapping_segment(segment, unique, start_time, end_time):
                continue
            unique.append(segment)
        return unique

    @staticmethod
    def _merge_overlapping_segment(
        incoming: SegmentWithScore,
        collected: List[SegmentWithScore],
        incoming_start: float,
        incoming_end: float,
    ) -> bool:
        for i, existing in enumerate(collected):
            existing_start = existing[SegmentKeys.START_TIME] - settings.EXTEND_BEFORE
            existing_end = existing[SegmentKeys.END_TIME] + settings.EXTEND_AFTER

            incoming_meta = incoming.get(EpisodeMetadataKeys.EPISODE_METADATA, {})
            existing_meta = existing.get(EpisodeMetadataKeys.EPISODE_METADATA, {})

            if (
                incoming_meta.get(EpisodeMetadataKeys.SEASON) == existing_meta.get(EpisodeMetadataKeys.SEASON)
                and incoming_meta.get(EpisodeMetadataKeys.EPISODE_NUMBER) == existing_meta.get(EpisodeMetadataKeys.EPISODE_NUMBER)
                and incoming_start <= existing_end
                and incoming_end >= existing_start
            ):
                collected[i][SegmentKeys.START_TIME] = min(
                    existing[SegmentKeys.START_TIME], incoming[SegmentKeys.START_TIME],
                )
                collected[i][SegmentKeys.END_TIME] = max(
                    existing[SegmentKeys.END_TIME], incoming[SegmentKeys.END_TIME],
                )
                collected[i][ElasticsearchKeys.SCORE] = max(
                    float(existing.get(ElasticsearchKeys.SCORE) or 0.0),
                    float(incoming.get(ElasticsearchKeys.SCORE) or 0.0),
                )
                return True
        return False

    @staticmethod
    def _build_index(series_names: List[str]) -> str:
        if not series_names:
            return f"*{ElasticsearchIndexSuffixes.SCENES}"
        return ",".join(f"{name}{ElasticsearchIndexSuffixes.SCENES}" for name in series_names)

    @staticmethod
    def _series_filter_clause(series_names: List[str]) -> List[Dict[str, Any]]:
        if not series_names:
            return []
        if len(series_names) == 1:
            return [{ElasticsearchQueryKeys.TERM: {EpisodeMetadataKeys.SERIES_NAME_FIELD: series_names[0]}}]
        return [{ElasticsearchQueryKeys.TERMS: {EpisodeMetadataKeys.SERIES_NAME_FIELD: series_names}}]

    @staticmethod
    async def find_by_filter(
        *,
        es: Any,
        series_names: List[str],
        search_filter: SearchFilter,
        size: int,
        logger: logging.Logger,
    ) -> List[SegmentWithScore]:
        filter_clauses = ScenesFinder._build_filter_clauses(search_filter)
        sort = ScenesFinder._build_sort(search_filter)

        query: Dict[str, Any] = {
            ElasticsearchQueryKeys.QUERY: {
                ElasticsearchQueryKeys.BOOL: {
                    ElasticsearchQueryKeys.FILTER: [
                        *ScenesFinder._series_filter_clause(series_names),
                        *filter_clauses,
                    ],
                },
            },
            ElasticsearchQueryKeys.SORT: sort,
            ElasticsearchQueryKeys.SOURCE: ScenesFinder.__SOURCE_FIELDS,
        }

        index_name = ScenesFinder._build_index(series_names)
        response = await es.search(index=index_name, body=query, size=size, ignore_unavailable=True)
        hits = response[ElasticsearchKeys.HITS][ElasticsearchKeys.HITS]

        series_desc = ",".join(series_names) if series_names else "all"
        await log_system_message(
            logging.INFO,
            f"ScenesFinder: {len(hits)} scenes found for series '{series_desc}'.",
            logger,
        )
        segments = ScenesFinder._attach_scores(hits)
        return ScenesFinder._deduplicate_hits(segments)

    @staticmethod
    async def find_by_text_and_filter(
        *,
        es: Any,
        series_names: List[str],
        quote: str,
        search_filter: Optional[SearchFilter],
        size: int,
        logger: logging.Logger,
    ) -> List[SegmentWithScore]:
        filter_clauses = ScenesFinder._build_filter_clauses(search_filter) if search_filter else []

        query: Dict[str, Any] = build_fuzzy_with_boost_query(
            field=SegmentKeys.TEXT,
            query=quote,
            filter_clauses=[
                *ScenesFinder._series_filter_clause(series_names),
                *filter_clauses,
            ],
        )
        query[ElasticsearchQueryKeys.SORT] = ScenesFinder._build_text_sort()
        query[ElasticsearchQueryKeys.SOURCE] = ScenesFinder.__SOURCE_FIELDS

        index_name = ScenesFinder._build_index(series_names)
        response = await es.search(index=index_name, body=query, size=size, ignore_unavailable=True)
        hits = response[ElasticsearchKeys.HITS][ElasticsearchKeys.HITS]

        series_desc = ",".join(series_names) if series_names else "all"
        await log_system_message(
            logging.INFO,
            f"ScenesFinder: {len(hits)} scenes found for quote '{quote}' in series '{series_desc}'.",
            logger,
        )
        segments = ScenesFinder._attach_scores(hits)
        return ScenesFinder._deduplicate_hits(segments)

    @staticmethod
    def _build_filter_clauses(search_filter: Optional[SearchFilter]) -> List[Dict[str, Any]]:
        if not search_filter:
            return []

        clauses = _build_season_episode_clauses(
            search_filter,
            EpisodeMetadataKeys.SEASON_FIELD,
            EpisodeMetadataKeys.EPISODE_NUMBER_FIELD,
        )

        for char_group in search_filter.get("character_groups", []):
            clauses.append(ScenesFinder._nested_character_clause(char_group))

        emotions = search_filter.get("emotions", [])
        if emotions:
            clauses.append(ScenesFinder._nested_emotion_clause(emotions))

        for obj_group in search_filter.get("object_groups", []):
            clauses.append(ScenesFinder._nested_object_clause(obj_group))

        return clauses

    @staticmethod
    def _nested_character_clause(char_names: List[str]) -> Dict[str, Any]:
        return {
            ElasticsearchQueryKeys.NESTED: {
                ElasticsearchQueryKeys.PATH: ScenesFinder.__FRAMES,
                ElasticsearchQueryKeys.QUERY: {
                    ElasticsearchQueryKeys.NESTED: {
                        ElasticsearchQueryKeys.PATH: ScenesFinder.__FRAMES_CHARACTERS,
                        ElasticsearchQueryKeys.QUERY: {
                            ElasticsearchQueryKeys.BOOL: {
                                ElasticsearchQueryKeys.SHOULD: [
                                    {
                                        ElasticsearchQueryKeys.TERM: {
                                            f"{ScenesFinder.__FRAMES_CHARACTERS}.{ActorKeys.NAME}": {
                                                ElasticsearchQueryKeys.VALUE: name,
                                                ElasticsearchQueryKeys.CASE_INSENSITIVE: True,
                                            },
                                        },
                                    }
                                    for name in char_names
                                ],
                                ElasticsearchQueryKeys.MINIMUM_SHOULD_MATCH: 1,
                            },
                        },
                    },
                },
            },
        }

    @staticmethod
    def _nested_emotion_clause(emotions: List[str]) -> Dict[str, Any]:
        labels_en = [en for e in emotions for en in (map_emotion_to_en(e),) if en]
        return {
            ElasticsearchQueryKeys.NESTED: {
                ElasticsearchQueryKeys.PATH: ScenesFinder.__FRAMES,
                ElasticsearchQueryKeys.QUERY: {
                    ElasticsearchQueryKeys.NESTED: {
                        ElasticsearchQueryKeys.PATH: ScenesFinder.__FRAMES_CHARACTERS,
                        ElasticsearchQueryKeys.QUERY: {
                            ElasticsearchQueryKeys.BOOL: {
                                ElasticsearchQueryKeys.SHOULD: [
                                    {
                                        ElasticsearchQueryKeys.TERM: {
                                            f"{ScenesFinder.__FRAMES_CHARACTERS}.{ActorKeys.EMOTION}.{EmotionKeys.LABEL}": label,
                                        },
                                    }
                                    for label in labels_en
                                ],
                                ElasticsearchQueryKeys.MINIMUM_SHOULD_MATCH: 1,
                            },
                        },
                    },
                },
            },
        }

    @staticmethod
    def _nested_object_clause(obj_group: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            ElasticsearchQueryKeys.NESTED: {
                ElasticsearchQueryKeys.PATH: ScenesFinder.__FRAMES,
                ElasticsearchQueryKeys.QUERY: {
                    ElasticsearchQueryKeys.NESTED: {
                        ElasticsearchQueryKeys.PATH: ScenesFinder.__FRAMES_OBJECTS,
                        ElasticsearchQueryKeys.QUERY: {
                            ElasticsearchQueryKeys.BOOL: {
                                ElasticsearchQueryKeys.SHOULD: [
                                    {
                                        ElasticsearchQueryKeys.TERM: {
                                            f"{ScenesFinder.__FRAMES_OBJECTS}.{DetectedObjectKeys.CLASS}": spec["name"],
                                        },
                                    }
                                    for spec in obj_group
                                ],
                                ElasticsearchQueryKeys.MINIMUM_SHOULD_MATCH: 1,
                            },
                        },
                        "score_mode": "max",
                    },
                },
            },
        }

    @staticmethod
    def _build_text_sort() -> List[Dict[str, Any]]:
        return [
            {ElasticsearchKeys.SCORE: {ElasticsearchQueryKeys.ORDER: ElasticsearchQueryKeys.DESC}},
            {EpisodeMetadataKeys.SEASON_FIELD: {ElasticsearchQueryKeys.ORDER: ElasticsearchQueryKeys.ASC}},
            {EpisodeMetadataKeys.EPISODE_NUMBER_FIELD: {ElasticsearchQueryKeys.ORDER: ElasticsearchQueryKeys.ASC}},
            {SegmentKeys.START_TIME: {ElasticsearchQueryKeys.ORDER: ElasticsearchQueryKeys.ASC}},
        ]

    @staticmethod
    def _build_sort(search_filter: Optional[SearchFilter]) -> List[Dict[str, Any]]:
        if not search_filter:
            return [
                {EpisodeMetadataKeys.SEASON_FIELD: {ElasticsearchQueryKeys.ORDER: ElasticsearchQueryKeys.ASC}},
                {EpisodeMetadataKeys.EPISODE_NUMBER_FIELD: {ElasticsearchQueryKeys.ORDER: ElasticsearchQueryKeys.ASC}},
                {SegmentKeys.START_TIME: {ElasticsearchQueryKeys.ORDER: ElasticsearchQueryKeys.ASC}},
            ]

        emotions = search_filter.get("emotions", [])
        character_groups = search_filter.get("character_groups", [])
        object_groups = search_filter.get("object_groups", [])

        has_emotion = bool(emotions)
        has_character = bool(character_groups)
        has_object = bool(object_groups)

        relevance_sort = ScenesFinder._build_relevance_sort(
            has_character, has_emotion, has_object,
            character_groups, emotions, object_groups,
        )
        if relevance_sort:
            return relevance_sort

        return [
            {EpisodeMetadataKeys.SEASON_FIELD: {ElasticsearchQueryKeys.ORDER: ElasticsearchQueryKeys.ASC}},
            {EpisodeMetadataKeys.EPISODE_NUMBER_FIELD: {ElasticsearchQueryKeys.ORDER: ElasticsearchQueryKeys.ASC}},
            {SegmentKeys.START_TIME: {ElasticsearchQueryKeys.ORDER: ElasticsearchQueryKeys.ASC}},
        ]

    @staticmethod
    def _build_relevance_sort(
        has_character: bool,
        has_emotion: bool,
        has_object: bool,
        character_groups: List[List[str]],
        emotions: List[str],
        object_groups: List[List[Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:
        sorts: List[Dict[str, Any]] = []

        if has_character:
            char_names = [name for group in character_groups for name in group]
            sorts.append({
                ScenesFinder.__CHAR_CONFIDENCE_FIELD: {
                    ElasticsearchQueryKeys.ORDER: "desc",
                    "mode": "max",
                    "nested": {
                        "path": ScenesFinder.__FRAMES,
                        "nested": {
                            "path": ScenesFinder.__FRAMES_CHARACTERS,
                            "filter": {
                                ElasticsearchQueryKeys.TERMS: {
                                    f"{ScenesFinder.__FRAMES_CHARACTERS}.{ActorKeys.NAME}": char_names,
                                },
                            },
                        },
                    },
                },
            })

        if has_emotion:
            labels_en = [en for e in emotions for en in (map_emotion_to_en(e),) if en]
            sorts.append({
                ScenesFinder.__EMOTION_CONFIDENCE_FIELD: {
                    ElasticsearchQueryKeys.ORDER: "desc",
                    "mode": "max",
                    "nested": {
                        "path": ScenesFinder.__FRAMES,
                        "nested": {
                            "path": ScenesFinder.__FRAMES_CHARACTERS,
                            "filter": {
                                ElasticsearchQueryKeys.TERMS: {
                                    f"{ScenesFinder.__FRAMES_CHARACTERS}.{ActorKeys.EMOTION}.{EmotionKeys.LABEL}": labels_en,
                                },
                            },
                        },
                    },
                },
            })

        if has_object:
            obj_names = [spec["name"] for group in object_groups for spec in group]
            sorts.append({
                ScenesFinder.__OBJECT_COUNT_FIELD: {
                    ElasticsearchQueryKeys.ORDER: "desc",
                    "mode": "max",
                    "nested": {
                        "path": ScenesFinder.__FRAMES,
                        "nested": {
                            "path": ScenesFinder.__FRAMES_OBJECTS,
                            "filter": {
                                ElasticsearchQueryKeys.TERMS: {
                                    f"{ScenesFinder.__FRAMES_OBJECTS}.{DetectedObjectKeys.CLASS}": obj_names,
                                },
                            },
                        },
                    },
                },
            })

        return sorts
