import difflib
import logging
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from bot.search.elastic_search_manager import (
    ElasticSearchManager,
    extract_hits,
)
from bot.types import (
    CharacterScene,
    CharacterWithEpisodeCount,
)
from bot.utils.constants import (
    ActorKeys,
    ElasticsearchAggregationKeys,
    ElasticsearchIndexSuffixes,
    ElasticsearchKeys,
    ElasticsearchQueryKeys,
    EmotionKeys,
    EpisodeMetadataKeys,
    SegmentKeys,
    VideoFrameKeys,
)
from bot.utils.log import log_system_message

_BACK_TO_ROOT = "back_to_root"
_NAMES_AGG = "names"
_SEASON_FIELD = f"{EpisodeMetadataKeys.EPISODE_METADATA}.{EpisodeMetadataKeys.SEASON}"
_EPISODE_FIELD = f"{EpisodeMetadataKeys.EPISODE_METADATA}.{EpisodeMetadataKeys.EPISODE_NUMBER}"


def _build_index(series_name: str) -> str:
    return f"{series_name}{ElasticsearchIndexSuffixes.VIDEO_FRAMES}"


def _character_field(subfield: str) -> str:
    return f"{ActorKeys.ACTORS}.{subfield}"


def _season_0_term() -> Dict[str, Any]:
    return {ElasticsearchQueryKeys.TERM: {_SEASON_FIELD: 0}}


def _char_term(character_name: str) -> Dict[str, Any]:
    return {
        ElasticsearchQueryKeys.TERM: {
            _character_field(ActorKeys.NAME): {
                ElasticsearchQueryKeys.VALUE: character_name,
                ElasticsearchQueryKeys.CASE_INSENSITIVE: True,
            },
        },
    }


def _nested_char_filter(character_name: str) -> Dict[str, Any]:
    return {
        ElasticsearchQueryKeys.NESTED: {
            ElasticsearchQueryKeys.PATH: ActorKeys.ACTORS,
            ElasticsearchQueryKeys.QUERY: _char_term(character_name),
        },
    }


def _parse_scene(source: Dict[str, Any], character_name: str) -> CharacterScene:
    meta = source.get(EpisodeMetadataKeys.EPISODE_METADATA, {})
    timestamp = source.get(VideoFrameKeys.TIMESTAMP, 0.0)
    scene: CharacterScene = {
        "season": meta.get(EpisodeMetadataKeys.SEASON, 0),
        "episode_number": meta.get(EpisodeMetadataKeys.EPISODE_NUMBER, 0),
        "title": meta.get(EpisodeMetadataKeys.TITLE, ""),
        "start_time": timestamp,
        "end_time": timestamp,
        "video_path": source.get(SegmentKeys.VIDEO_PATH, ""),
    }
    for appearance in source.get(ActorKeys.ACTORS, []):
        if not isinstance(appearance, dict):
            continue
        if appearance.get(ActorKeys.NAME, "").lower() == character_name.lower():
            if ActorKeys.CONFIDENCE in appearance:
                scene["actor_confidence"] = appearance[ActorKeys.CONFIDENCE]
            emotion = appearance.get(ActorKeys.EMOTION)
            if isinstance(emotion, dict):
                if EmotionKeys.LABEL in emotion:
                    scene["emotion_label"] = emotion[EmotionKeys.LABEL]
                if EmotionKeys.CONFIDENCE in emotion:
                    scene["emotion_confidence"] = emotion[EmotionKeys.CONFIDENCE]
            break
    return scene



def _confidence_sort(character_name: str) -> Dict[str, Any]:
    return {
        _character_field(ActorKeys.CONFIDENCE): {
            ElasticsearchQueryKeys.ORDER: ElasticsearchQueryKeys.DESC,
            ElasticsearchQueryKeys.NESTED: {
                ElasticsearchQueryKeys.PATH: ActorKeys.ACTORS,
                ElasticsearchQueryKeys.FILTER: _char_term(character_name),
            },
            ElasticsearchQueryKeys.MODE: ElasticsearchQueryKeys.MAX,
        },
    }


def _emotion_confidence_sort(character_name: str, emotion_en: str) -> Dict[str, Any]:
    return {
        _character_field(f"{ActorKeys.EMOTION}.{EmotionKeys.CONFIDENCE}"): {
            ElasticsearchQueryKeys.ORDER: ElasticsearchQueryKeys.DESC,
            ElasticsearchQueryKeys.NESTED: {
                ElasticsearchQueryKeys.PATH: ActorKeys.ACTORS,
                ElasticsearchQueryKeys.FILTER: {
                    ElasticsearchQueryKeys.BOOL: {
                        ElasticsearchQueryKeys.MUST: [
                            _char_term(character_name),
                            {
                                ElasticsearchQueryKeys.TERM: {
                                    _character_field(f"{ActorKeys.EMOTION}.{EmotionKeys.LABEL}"): emotion_en,
                                },
                            },
                        ],
                    },
                },
            },
            ElasticsearchQueryKeys.MODE: ElasticsearchQueryKeys.MAX,
        },
    }


def _episode_sort() -> List[Dict[str, Any]]:
    return [
        {_SEASON_FIELD: ElasticsearchQueryKeys.ASC},
        {_EPISODE_FIELD: ElasticsearchQueryKeys.ASC},
        {VideoFrameKeys.TIMESTAMP: ElasticsearchQueryKeys.ASC},
    ]


class CharacterFinder:
    @staticmethod
    async def get_all_characters(
        series_name: str,
        logger: logging.Logger,
    ) -> List[CharacterWithEpisodeCount]:
        await log_system_message(logging.INFO, f"Fetching all characters for series '{series_name}'.", logger)
        es = await ElasticSearchManager.connect_to_elasticsearch(logger)

        query = {
            ElasticsearchQueryKeys.SIZE: 0,
            ElasticsearchQueryKeys.QUERY: {
                ElasticsearchQueryKeys.BOOL: {
                    ElasticsearchQueryKeys.MUST_NOT: [_season_0_term()],
                },
            },
            ElasticsearchQueryKeys.AGGS: {
                ElasticsearchAggregationKeys.ACTORS: {
                    ElasticsearchQueryKeys.NESTED: {ElasticsearchQueryKeys.PATH: ActorKeys.ACTORS},
                    ElasticsearchQueryKeys.AGGS: {
                        _NAMES_AGG: {
                            ElasticsearchQueryKeys.TERMS: {
                                ElasticsearchQueryKeys.FIELD: _character_field(ActorKeys.NAME),
                                ElasticsearchQueryKeys.SIZE: 10000,
                                ElasticsearchQueryKeys.ORDER: {ElasticsearchQueryKeys.KEY: ElasticsearchQueryKeys.ASC},
                            },
                            ElasticsearchQueryKeys.AGGS: {
                                _BACK_TO_ROOT: {
                                    ElasticsearchQueryKeys.REVERSE_NESTED: {},
                                    ElasticsearchQueryKeys.AGGS: {
                                        ElasticsearchAggregationKeys.UNIQUE_EPISODES: {
                                            ElasticsearchQueryKeys.CARDINALITY: {
                                                ElasticsearchQueryKeys.FIELD: VideoFrameKeys.EPISODE_ID,
                                            },
                                        },
                                    },
                                },
                            },
                        },
                    },
                },
            },
        }

        response = await es.search(index=_build_index(series_name), body=query)
        buckets = (
            response[ElasticsearchKeys.AGGREGATIONS]
            [ElasticsearchAggregationKeys.ACTORS]
            [_NAMES_AGG]
            [ElasticsearchKeys.BUCKETS]
        )
        characters = [
            CharacterWithEpisodeCount(
                name=b[ElasticsearchKeys.KEY],
                episode_count=b[_BACK_TO_ROOT][ElasticsearchAggregationKeys.UNIQUE_EPISODES][ElasticsearchAggregationKeys.VALUE],
            )
            for b in buckets
        ]
        await log_system_message(logging.INFO, f"Found {len(characters)} characters.", logger)
        return characters

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

        query = {
            ElasticsearchQueryKeys.QUERY: {
                ElasticsearchQueryKeys.BOOL: {
                    ElasticsearchQueryKeys.FILTER: [_nested_char_filter(character_name)],
                    ElasticsearchQueryKeys.MUST_NOT: [_season_0_term()],
                },
            },
            ElasticsearchQueryKeys.SORT: [
                _confidence_sort(character_name),
                *_episode_sort(),
            ],
            ElasticsearchQueryKeys.SIZE: 999,
        }

        response = await es.search(index=_build_index(series_name), body=query)
        hits = extract_hits(response)
        scenes = [_parse_scene(h[ElasticsearchKeys.SOURCE], character_name) for h in hits]
        await log_system_message(logging.INFO, f"Found {len(scenes)} scenes for '{character_name}'.", logger)
        return scenes

    @staticmethod
    async def get_scenes_by_character_and_emotion(
        character_name: str,
        emotion_en: str,
        series_name: str,
        logger: logging.Logger,
    ) -> List[CharacterScene]:
        await log_system_message(
            logging.INFO,
            f"Fetching scenes for '{character_name}' with emotion '{emotion_en}' in '{series_name}'.",
            logger,
        )
        es = await ElasticSearchManager.connect_to_elasticsearch(logger)

        char_and_emotion_nested = {
            ElasticsearchQueryKeys.NESTED: {
                ElasticsearchQueryKeys.PATH: ActorKeys.ACTORS,
                ElasticsearchQueryKeys.QUERY: {
                    ElasticsearchQueryKeys.BOOL: {
                        ElasticsearchQueryKeys.MUST: [
                            _char_term(character_name),
                            {
                                ElasticsearchQueryKeys.TERM: {
                                    _character_field(f"{ActorKeys.EMOTION}.{EmotionKeys.LABEL}"): emotion_en,
                                },
                            },
                        ],
                    },
                },
            },
        }

        query = {
            ElasticsearchQueryKeys.QUERY: {
                ElasticsearchQueryKeys.BOOL: {
                    ElasticsearchQueryKeys.FILTER: [char_and_emotion_nested],
                    ElasticsearchQueryKeys.MUST_NOT: [_season_0_term()],
                },
            },
            ElasticsearchQueryKeys.SORT: [
                _emotion_confidence_sort(character_name, emotion_en),
                _confidence_sort(character_name),
                *_episode_sort(),
            ],
            ElasticsearchQueryKeys.SIZE: 999,
        }

        response = await es.search(index=_build_index(series_name), body=query)
        hits = extract_hits(response)
        scenes = [_parse_scene(h[ElasticsearchKeys.SOURCE], character_name) for h in hits]
        await log_system_message(
            logging.INFO, f"Found {len(scenes)} scenes for '{character_name}' with emotion '{emotion_en}'.", logger,
        )
        return scenes

    @staticmethod
    async def get_all_emotions(
        series_name: str,
        logger: logging.Logger,
    ) -> List[str]:
        await log_system_message(logging.INFO, f"Fetching all emotions for series '{series_name}'.", logger)
        es = await ElasticSearchManager.connect_to_elasticsearch(logger)

        query = {
            ElasticsearchQueryKeys.SIZE: 0,
            ElasticsearchQueryKeys.AGGS: {
                ElasticsearchAggregationKeys.ACTORS: {
                    ElasticsearchQueryKeys.NESTED: {ElasticsearchQueryKeys.PATH: ActorKeys.ACTORS},
                    ElasticsearchQueryKeys.AGGS: {
                        ElasticsearchAggregationKeys.EMOTION_LABELS: {
                            ElasticsearchQueryKeys.TERMS: {
                                ElasticsearchQueryKeys.FIELD: _character_field(
                                    f"{ActorKeys.EMOTION}.{EmotionKeys.LABEL}",
                                ),
                                ElasticsearchQueryKeys.SIZE: 100,
                            },
                        },
                    },
                },
            },
        }

        response = await es.search(index=_build_index(series_name), body=query)
        buckets = (
            response[ElasticsearchKeys.AGGREGATIONS]
            [ElasticsearchAggregationKeys.ACTORS]
            [ElasticsearchAggregationKeys.EMOTION_LABELS]
            [ElasticsearchKeys.BUCKETS]
        )
        labels = [b[ElasticsearchKeys.KEY] for b in buckets]
        await log_system_message(logging.INFO, f"Found {len(labels)} unique emotion labels.", logger)
        return labels

    @staticmethod
    async def find_best_matching_name(
        query: str,
        series_name: str,
        logger: logging.Logger,
    ) -> Optional[str]:
        characters = await CharacterFinder.get_all_characters(series_name, logger)
        names = [c["name"] for c in characters]
        name_map = {n.lower(): n for n in names}
        if query.lower() in name_map:
            return name_map[query.lower()]
        matches = difflib.get_close_matches(query.lower(), list(name_map.keys()), n=1, cutoff=0.6)
        return name_map[matches[0]] if matches else None
