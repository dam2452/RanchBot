import logging
from typing import (
    Any,
    Dict,
    List,
)

from bot.search.elastic_search_manager import ElasticSearchManager
from bot.types import (
    CharacterScene,
    CharacterWithEpisodeCount,
)
from bot.utils.constants import (
    ActorKeys,
    ElasticsearchAggregationKeys,
    ElasticsearchKeys,
    ElasticsearchQueryKeys,
    EmotionKeys,
    EpisodeMetadataKeys,
    SegmentKeys,
)
from bot.utils.log import log_system_message


def _build_index(series_name: str) -> str:
    return f"{series_name}_text_segments"


def _parse_scene(source: Dict[str, Any], character_name: str) -> CharacterScene:
    meta = source.get(EpisodeMetadataKeys.EPISODE_METADATA, source.get(EpisodeMetadataKeys.EPISODE_INFO, {}))
    scene: CharacterScene = {
        "season": meta.get(EpisodeMetadataKeys.SEASON, 0),
        "episode_number": meta.get(EpisodeMetadataKeys.EPISODE_NUMBER, 0),
        "title": meta.get(EpisodeMetadataKeys.TITLE, ""),
        "start_time": source.get(SegmentKeys.START_TIME, source.get(SegmentKeys.START, 0.0)),
        "end_time": source.get(SegmentKeys.END_TIME, source.get(SegmentKeys.END, 0.0)),
    }
    if SegmentKeys.VIDEO_PATH in source:
        scene["video_path"] = source[SegmentKeys.VIDEO_PATH]

    actors = source.get(ActorKeys.ACTORS, [])
    for actor in actors:
        if not isinstance(actor, dict):
            continue
        if actor.get(ActorKeys.NAME, "").lower() == character_name.lower():
            if ActorKeys.CONFIDENCE in actor:
                scene["actor_confidence"] = actor[ActorKeys.CONFIDENCE]
            emotion = actor.get(ActorKeys.EMOTION)
            if isinstance(emotion, dict):
                if EmotionKeys.LABEL in emotion:
                    scene["emotion_label"] = emotion[EmotionKeys.LABEL]
                if EmotionKeys.CONFIDENCE in emotion:
                    scene["emotion_confidence"] = emotion[EmotionKeys.CONFIDENCE]
            break

    return scene


class CharacterFinder:
    @staticmethod
    async def get_all_characters(
        series_name: str,
        logger: logging.Logger,
    ) -> List[CharacterWithEpisodeCount]:
        await log_system_message(
            logging.INFO,
            f"Fetching all characters for series '{series_name}'.",
            logger,
        )
        es = await ElasticSearchManager.connect_to_elasticsearch(logger)
        index = _build_index(series_name)

        base_query: Dict[str, Any] = {
            ElasticsearchQueryKeys.SIZE: 0,
            ElasticsearchQueryKeys.QUERY: {
                ElasticsearchQueryKeys.BOOL: {
                    "must_not": [
                        {
                            ElasticsearchQueryKeys.TERM: {
                                f"{EpisodeMetadataKeys.EPISODE_METADATA}.{EpisodeMetadataKeys.SEASON}": 0,
                            },
                        },
                    ],
                },
            },
        }

        def __build_agg_query(field: str) -> Dict[str, Any]:
            query = dict(base_query)
            query[ElasticsearchQueryKeys.AGGS] = {
                ElasticsearchAggregationKeys.ACTORS: {
                    ElasticsearchQueryKeys.TERMS: {
                        ElasticsearchQueryKeys.FIELD: field,
                        ElasticsearchQueryKeys.SIZE: 10000,
                        ElasticsearchQueryKeys.ORDER: {ElasticsearchQueryKeys.KEY: ElasticsearchQueryKeys.ASC},
                    },
                    ElasticsearchQueryKeys.AGGS: {
                        ElasticsearchAggregationKeys.UNIQUE_EPISODES: {
                            ElasticsearchQueryKeys.CARDINALITY: {
                                ElasticsearchQueryKeys.FIELD: "episode_id",
                            },
                        },
                    },
                },
            }
            return query

        for field in (f"{ActorKeys.ACTORS}.{ActorKeys.NAME}.keyword", f"{ActorKeys.ACTORS}.keyword"):
            response = await es.search(index=index, body=__build_agg_query(field))
            buckets = response[ElasticsearchKeys.AGGREGATIONS][ElasticsearchAggregationKeys.ACTORS][ElasticsearchKeys.BUCKETS]
            if buckets:
                return [
                    CharacterWithEpisodeCount(
                        name=b[ElasticsearchKeys.KEY],
                        episode_count=b[ElasticsearchAggregationKeys.UNIQUE_EPISODES][ElasticsearchAggregationKeys.VALUE],
                    )
                    for b in buckets
                ]

        await log_system_message(logging.INFO, "No characters found.", logger)
        return []

    @staticmethod
    async def get_scenes_by_character(
        character_name: str,
        series_name: str,
        logger: logging.Logger,
    ) -> List[CharacterScene]:
        await log_system_message(
            logging.INFO,
            f"Fetching scenes for character '{character_name}' in series '{series_name}'.",
            logger,
        )
        es = await ElasticSearchManager.connect_to_elasticsearch(logger)
        index = _build_index(series_name)

        season_filter = {
            ElasticsearchQueryKeys.BOOL: {
                "must_not": [{
                    ElasticsearchQueryKeys.TERM: {
                        f"{EpisodeMetadataKeys.EPISODE_METADATA}.{EpisodeMetadataKeys.SEASON}": 0,
                    },
                }],
            },
        }

        def __build_query(actor_filter: Dict[str, Any]) -> Dict[str, Any]:
            return {
                ElasticsearchQueryKeys.QUERY: {
                    ElasticsearchQueryKeys.BOOL: {
                        ElasticsearchQueryKeys.FILTER: [actor_filter, season_filter],
                    },
                },
                ElasticsearchQueryKeys.SORT: [
                    {f"{EpisodeMetadataKeys.EPISODE_METADATA}.{EpisodeMetadataKeys.SEASON}": {ElasticsearchQueryKeys.ORDER: ElasticsearchQueryKeys.ASC}},
                    {
                        f"{EpisodeMetadataKeys.EPISODE_METADATA}.{EpisodeMetadataKeys.EPISODE_NUMBER}": {
                            ElasticsearchQueryKeys.ORDER: ElasticsearchQueryKeys.ASC,
                        },
                    },
                    {SegmentKeys.START_TIME: {ElasticsearchQueryKeys.ORDER: ElasticsearchQueryKeys.ASC}},
                ],
                ElasticsearchQueryKeys.SIZE: 999,
            }

        actor_name_filter = {ElasticsearchQueryKeys.MATCH: {f"{ActorKeys.ACTORS}.{ActorKeys.NAME}": character_name}}
        actor_keyword_filter = {ElasticsearchQueryKeys.TERM: {f"{ActorKeys.ACTORS}.keyword": character_name}}

        for actor_filter in (actor_name_filter, actor_keyword_filter):
            response = await es.search(index=index, body=__build_query(actor_filter))
            hits = response[ElasticsearchKeys.HITS][ElasticsearchKeys.HITS]
            if hits:
                scenes = [_parse_scene(h[ElasticsearchKeys.SOURCE], character_name) for h in hits]
                scenes.sort(
                    key=lambda s: (
                        -s.get("actor_confidence", 0.0),
                        s["season"],
                        s["episode_number"],
                        s["start_time"],
                    ),
                )
                await log_system_message(logging.INFO, f"Found {len(scenes)} scenes for '{character_name}'.", logger)
                return scenes

        await log_system_message(logging.INFO, f"No scenes found for character '{character_name}'.", logger)
        return []

    @staticmethod
    async def get_scenes_by_character_and_emotion(
        character_name: str,
        emotion_en: str,
        series_name: str,
        logger: logging.Logger,
    ) -> List[CharacterScene]:
        await log_system_message(
            logging.INFO,
            f"Fetching scenes for character '{character_name}' with emotion '{emotion_en}' in series '{series_name}'.",
            logger,
        )
        es = await ElasticSearchManager.connect_to_elasticsearch(logger)
        index = _build_index(series_name)

        query: Dict[str, Any] = {
            ElasticsearchQueryKeys.QUERY: {
                ElasticsearchQueryKeys.BOOL: {
                    ElasticsearchQueryKeys.FILTER: [
                        {ElasticsearchQueryKeys.MATCH: {f"{ActorKeys.ACTORS}.{ActorKeys.NAME}": character_name}},
                        {ElasticsearchQueryKeys.TERM: {f"{ActorKeys.ACTORS}.{ActorKeys.EMOTION}.{EmotionKeys.LABEL}.keyword": emotion_en}},
                    ],
                    "must_not": [{
                        ElasticsearchQueryKeys.TERM: {
                            f"{EpisodeMetadataKeys.EPISODE_METADATA}.{EpisodeMetadataKeys.SEASON}": 0,
                        },
                    }],
                },
            },
            ElasticsearchQueryKeys.SORT: [
                {f"{EpisodeMetadataKeys.EPISODE_METADATA}.{EpisodeMetadataKeys.SEASON}": {ElasticsearchQueryKeys.ORDER: ElasticsearchQueryKeys.ASC}},
                {f"{EpisodeMetadataKeys.EPISODE_METADATA}.{EpisodeMetadataKeys.EPISODE_NUMBER}": {ElasticsearchQueryKeys.ORDER: ElasticsearchQueryKeys.ASC}},
                {SegmentKeys.START_TIME: {ElasticsearchQueryKeys.ORDER: ElasticsearchQueryKeys.ASC}},
            ],
            ElasticsearchQueryKeys.SIZE: 999,
        }

        response = await es.search(index=index, body=query)
        hits = response[ElasticsearchKeys.HITS][ElasticsearchKeys.HITS]

        scenes = [_parse_scene(h[ElasticsearchKeys.SOURCE], character_name) for h in hits]
        scenes.sort(
            key=lambda s: (
                -s.get("emotion_confidence", 0.0),
                -s.get("actor_confidence", 0.0),
                s["season"],
                s["episode_number"],
                s["start_time"],
            ),
        )

        await log_system_message(
            logging.INFO,
            f"Found {len(scenes)} scenes for '{character_name}' with emotion '{emotion_en}'.",
            logger,
        )
        return scenes

    @staticmethod
    async def get_all_emotions(
        series_name: str,
        logger: logging.Logger,
    ) -> List[str]:
        await log_system_message(
            logging.INFO,
            f"Fetching all emotions for series '{series_name}'.",
            logger,
        )
        es = await ElasticSearchManager.connect_to_elasticsearch(logger)
        index = _build_index(series_name)

        query: Dict[str, Any] = {
            ElasticsearchQueryKeys.SIZE: 0,
            ElasticsearchQueryKeys.AGGS: {
                "actors_nested": {
                    "nested": {"path": ActorKeys.ACTORS},
                    ElasticsearchQueryKeys.AGGS: {
                        ElasticsearchAggregationKeys.EMOTION_LABELS: {
                            ElasticsearchQueryKeys.TERMS: {
                                ElasticsearchQueryKeys.FIELD: f"{ActorKeys.ACTORS}.{ActorKeys.EMOTION}.{EmotionKeys.LABEL}.keyword",
                                ElasticsearchQueryKeys.SIZE: 100,
                            },
                        },
                    },
                },
            },
        }

        try:
            response = await es.search(index=index, body=query)
            buckets = (
                response[ElasticsearchKeys.AGGREGATIONS]["actors_nested"]
                [ElasticsearchAggregationKeys.EMOTION_LABELS][ElasticsearchKeys.BUCKETS]
            )
            labels = [b[ElasticsearchKeys.KEY] for b in buckets]
        except Exception:
            flat_query: Dict[str, Any] = {
                ElasticsearchQueryKeys.SIZE: 0,
                ElasticsearchQueryKeys.AGGS: {
                    ElasticsearchAggregationKeys.EMOTION_LABELS: {
                        ElasticsearchQueryKeys.TERMS: {
                            ElasticsearchQueryKeys.FIELD: f"{ActorKeys.ACTORS}.{ActorKeys.EMOTION}.{EmotionKeys.LABEL}.keyword",
                            ElasticsearchQueryKeys.SIZE: 100,
                        },
                    },
                },
            }
            response = await es.search(index=index, body=flat_query)
            buckets = response[ElasticsearchKeys.AGGREGATIONS][ElasticsearchAggregationKeys.EMOTION_LABELS][ElasticsearchKeys.BUCKETS]
            labels = [b[ElasticsearchKeys.KEY] for b in buckets]

        await log_system_message(logging.INFO, f"Found {len(labels)} unique emotion labels.", logger)
        return labels
