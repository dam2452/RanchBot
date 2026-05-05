import logging
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from bot.responses.not_sending_videos.emotions_handler_responses import map_emotion_to_en
from bot.search.filter_applicator import _build_season_episode_clauses
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
    __EMOTION_CONFIDENCE_FIELD = (
        f"{__FRAMES}.{ActorKeys.ACTORS}.{ActorKeys.EMOTION}.{EmotionKeys.CONFIDENCE}"
    )

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
    def _index(series_name: str) -> str:
        return f"{series_name}{ElasticsearchIndexSuffixes.SCENES}"

    @staticmethod
    async def find_by_filter(
        *,
        es: Any,
        series_name: str,
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
                        {ElasticsearchQueryKeys.TERM: {EpisodeMetadataKeys.SERIES_NAME_FIELD: series_name}},
                        *filter_clauses,
                    ],
                },
            },
            ElasticsearchQueryKeys.SORT: sort,
            ElasticsearchQueryKeys.SOURCE: ScenesFinder.__SOURCE_FIELDS,
        }

        response = await es.search(index=ScenesFinder._index(series_name), body=query, size=size)
        hits = response[ElasticsearchKeys.HITS][ElasticsearchKeys.HITS]

        await log_system_message(
            logging.INFO,
            f"ScenesFinder: {len(hits)} scenes found for series '{series_name}'.",
            logger,
        )
        return [hit[ElasticsearchKeys.SOURCE] for hit in hits]

    @staticmethod
    async def find_by_text_and_filter(
        *,
        es: Any,
        series_name: str,
        quote: str,
        search_filter: Optional[SearchFilter],
        size: int,
        logger: logging.Logger,
    ) -> List[SegmentWithScore]:
        filter_clauses = ScenesFinder._build_filter_clauses(search_filter) if search_filter else []

        query: Dict[str, Any] = {
            ElasticsearchQueryKeys.QUERY: {
                ElasticsearchQueryKeys.BOOL: {
                    ElasticsearchQueryKeys.MUST: [
                        {ElasticsearchQueryKeys.MATCH: {"text": quote}},
                    ],
                    ElasticsearchQueryKeys.FILTER: [
                        {ElasticsearchQueryKeys.TERM: {EpisodeMetadataKeys.SERIES_NAME_FIELD: series_name}},
                        *filter_clauses,
                    ],
                },
            },
            ElasticsearchQueryKeys.SOURCE: ScenesFinder.__SOURCE_FIELDS,
        }

        response = await es.search(index=ScenesFinder._index(series_name), body=query, size=size)
        hits = response[ElasticsearchKeys.HITS][ElasticsearchKeys.HITS]

        await log_system_message(
            logging.INFO,
            f"ScenesFinder: {len(hits)} scenes found for quote '{quote}' in series '{series_name}'.",
            logger,
        )
        return [hit[ElasticsearchKeys.SOURCE] for hit in hits]

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
    def _build_sort(search_filter: Optional[SearchFilter]) -> List[Dict[str, Any]]:
        emotions = (search_filter or {}).get("emotions", [])
        character_groups = (search_filter or {}).get("character_groups", [])
        object_groups = (search_filter or {}).get("object_groups", [])

        emotion_only = emotions and not character_groups and not object_groups
        if not emotion_only:
            return [
                {EpisodeMetadataKeys.SEASON_FIELD: {ElasticsearchQueryKeys.ORDER: ElasticsearchQueryKeys.ASC}},
                {EpisodeMetadataKeys.EPISODE_NUMBER_FIELD: {ElasticsearchQueryKeys.ORDER: ElasticsearchQueryKeys.ASC}},
                {SegmentKeys.START_TIME: {ElasticsearchQueryKeys.ORDER: ElasticsearchQueryKeys.ASC}},
            ]

        labels_en = [en for e in emotions for en in (map_emotion_to_en(e),) if en]
        return [
            {
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
            },
        ]
