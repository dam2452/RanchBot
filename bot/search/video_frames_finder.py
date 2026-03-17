# pylint: disable=duplicate-code
import difflib
import logging
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from bidict import bidict

from bot.search.infra.elastic_search_manager import ElasticSearchManager
from bot.settings import settings
from bot.types import (
    CharacterScene,
    CharacterWithEpisodeCount,
    ObjectScene,
    ObjectWithCount,
    QuantityFilter,
)
from bot.utils.constants import (
    ActorKeys,
    DetectedObjectKeys,
    ElasticsearchAggregationKeys,
    ElasticsearchIndexSuffixes,
    ElasticsearchKeys,
    ElasticsearchQueryKeys,
    EmotionKeys,
    EpisodeMetadataKeys,
    SceneInfoKeys,
    SegmentKeys,
    VideoFrameKeys,
)
from bot.utils.log import log_system_message

_SEASON_FIELD = EpisodeMetadataKeys.SEASON_FIELD
_EPISODE_FIELD = EpisodeMetadataKeys.EPISODE_NUMBER_FIELD
_OBJECT_CLASS_FIELD = f"{VideoFrameKeys.DETECTED_OBJECTS}.class"
_BACK_TO_ROOT = "back_to_root"
_NAMES_AGG = "names"
_OBJECTS_AGG = "objects"
_CLASSES_AGG = "classes"
_DOC_COUNT = "doc_count"

_OPERATORS = {
    "=": lambda c, v: c == v,
    ">": lambda c, v: c > v,
    "<": lambda c, v: c < v,
    ">=": lambda c, v: c >= v,
    "<=": lambda c, v: c <= v,
}

_OBJECT_NAMES: bidict[str, str] = bidict({
    "person": "osoba",
    "bicycle": "rower",
    "car": "samochód",
    "motorbike": "motocykl",
    "aeroplane": "samolot",
    "bus": "autobus",
    "train": "pociąg",
    "truck": "ciężarówka",
    "boat": "łódź",
    "horse": "koń",
    "cow": "krowa",
    "sheep": "owca",
    "dog": "pies",
    "cat": "kot",
    "bird": "ptak",
    "chair": "krzesło",
    "sofa": "kanapa",
    "diningtable": "stół",
    "tvmonitor": "telewizor",
    "laptop": "laptop",
    "cell phone": "telefon",
    "bottle": "butelka",
    "cup": "kubek",
    "bowl": "miska",
    "knife": "nóż",
    "fork": "widelec",
    "spoon": "łyżka",
    "backpack": "plecak",
    "handbag": "torebka",
    "suitcase": "walizka",
    "clock": "zegar",
    "book": "książka",
    "vase": "wazon",
    "tie": "krawat",
    "umbrella": "parasol",
    "apple": "jabłko",
    "banana": "banan",
    "carrot": "marchew",
    "orange": "pomarańcza",
    "pizza": "pizza",
    "sandwich": "kanapka",
    "cake": "ciasto",
    "donut": "pączek",
    "broccoli": "brokuł",
    "hot dog": "hot dog",
    "wine glass": "kieliszek",
    "scissors": "nożyczki",
    "toothbrush": "szczoteczka",
    "keyboard": "klawiatura",
    "mouse": "myszka",
    "remote": "pilot",
    "refrigerator": "lodówka",
    "microwave": "kuchenka",
    "oven": "piekarnik",
    "toaster": "toster",
    "sink": "zlew",
    "toilet": "toaleta",
    "bed": "łóżko",
    "bench": "ławka",
    "bear": "niedźwiedź",
    "elephant": "słoń",
    "giraffe": "żyrafa",
    "teddy bear": "miś",
    "kite": "latawiec",
    "skis": "narty",
    "skateboard": "deskorolka",
    "surfboard": "deska surfingowa",
    "tennis racket": "rakieta tenisowa",
    "frisbee": "frisbee",
    "sports ball": "piłka",
    "fire hydrant": "hydrant",
    "parking meter": "parkometr",
    "stop sign": "znak stop",
    "traffic light": "sygnalizacja",
    "pottedplant": "roślina doniczkowa",
    "hair drier": "suszarka",
    "baseball bat": "kij bejsbolowy",
    "baseball glove": "rękawica bejsbolowa",
    "snowboard": "snowboard",
})


def _build_index(series_name: str) -> str:
    return f"{series_name}{ElasticsearchIndexSuffixes.VIDEO_FRAMES}"


def get_polish_name(class_name: str) -> str:
    return _OBJECT_NAMES.get(class_name.lower(), class_name)


class VideoFramesFinder:
    @staticmethod
    async def find_frames_in_episode(
        season: int,
        episode_number: int,
        series_name: str,
        logger: logging.Logger,
    ) -> List[Dict[str, Any]]:
        await log_system_message(
            logging.INFO,
            f"Fetching frames for S{season:02d}E{episode_number:02d} in '{series_name}'.",
            logger,
        )
        es = await ElasticSearchManager.connect_to_elasticsearch(logger)

        query = {
            ElasticsearchQueryKeys.QUERY: {
                ElasticsearchQueryKeys.BOOL: {
                    ElasticsearchQueryKeys.MUST: [
                        {ElasticsearchQueryKeys.TERM: {_SEASON_FIELD: season}},
                        {ElasticsearchQueryKeys.TERM: {_EPISODE_FIELD: episode_number}},
                    ],
                },
            },
            ElasticsearchQueryKeys.SORT: [{VideoFrameKeys.TIMESTAMP: ElasticsearchQueryKeys.ASC}],
            ElasticsearchQueryKeys.SIZE: settings.MAX_ES_RESULTS_LONG,
        }

        response = await es.search(index=_build_index(series_name), body=query)
        hits = response[ElasticsearchKeys.HITS][ElasticsearchKeys.HITS]
        frames = [h[ElasticsearchKeys.SOURCE] for h in hits]
        await log_system_message(
            logging.INFO, f"Found {len(frames)} frames for S{season:02d}E{episode_number:02d}.", logger,
        )
        return frames

    @staticmethod
    async def find_frames_near_timestamp(
        season: int,
        episode_number: int,
        timestamp: float,
        radius_seconds: float,
        series_name: str,
        logger: logging.Logger,
    ) -> List[Dict[str, Any]]:
        await log_system_message(
            logging.INFO,
            f"Fetching frames near {timestamp:.2f}s (±{radius_seconds}s) in S{season:02d}E{episode_number:02d}.",
            logger,
        )
        es = await ElasticSearchManager.connect_to_elasticsearch(logger)

        query = {
            ElasticsearchQueryKeys.QUERY: {
                ElasticsearchQueryKeys.BOOL: {
                    ElasticsearchQueryKeys.MUST: [
                        {ElasticsearchQueryKeys.TERM: {_SEASON_FIELD: season}},
                        {ElasticsearchQueryKeys.TERM: {_EPISODE_FIELD: episode_number}},
                        {
                            ElasticsearchQueryKeys.RANGE: {
                                VideoFrameKeys.TIMESTAMP: {
                                    ElasticsearchQueryKeys.GT: timestamp - radius_seconds,
                                    ElasticsearchQueryKeys.LT: timestamp + radius_seconds,
                                },
                            },
                        },
                    ],
                },
            },
            ElasticsearchQueryKeys.SORT: [{VideoFrameKeys.TIMESTAMP: ElasticsearchQueryKeys.ASC}],
            ElasticsearchQueryKeys.SIZE: 100,
        }

        response = await es.search(index=_build_index(series_name), body=query)
        hits = response[ElasticsearchKeys.HITS][ElasticsearchKeys.HITS]
        return [h[ElasticsearchKeys.SOURCE] for h in hits]

    @staticmethod
    async def find_frames_with_detected_object(
        object_class: str,
        series_name: str,
        logger: logging.Logger,
        season_filter: Optional[int] = None,
        episode_filter: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        await log_system_message(
            logging.INFO, f"Fetching frames with object '{object_class}' in '{series_name}'.", logger,
        )
        es = await ElasticSearchManager.connect_to_elasticsearch(logger)

        must_clauses: List[Dict[str, Any]] = [
            {
                ElasticsearchQueryKeys.NESTED: {
                    ElasticsearchQueryKeys.PATH: VideoFrameKeys.DETECTED_OBJECTS,
                    ElasticsearchQueryKeys.QUERY: {
                        ElasticsearchQueryKeys.TERM: {_OBJECT_CLASS_FIELD: object_class},
                    },
                },
            },
        ]
        if season_filter is not None:
            must_clauses.append({ElasticsearchQueryKeys.TERM: {_SEASON_FIELD: season_filter}})
        if episode_filter is not None:
            must_clauses.append({ElasticsearchQueryKeys.TERM: {_EPISODE_FIELD: episode_filter}})

        object_count_field = f"{VideoFrameKeys.DETECTED_OBJECTS}.count"
        query = {
            ElasticsearchQueryKeys.QUERY: {
                ElasticsearchQueryKeys.BOOL: {ElasticsearchQueryKeys.MUST: must_clauses},
            },
            ElasticsearchQueryKeys.SORT: [
                {
                    object_count_field: {
                        ElasticsearchQueryKeys.ORDER: ElasticsearchQueryKeys.DESC,
                        ElasticsearchQueryKeys.NESTED: {
                            ElasticsearchQueryKeys.PATH: VideoFrameKeys.DETECTED_OBJECTS,
                            ElasticsearchQueryKeys.FILTER: {
                                ElasticsearchQueryKeys.TERM: {_OBJECT_CLASS_FIELD: object_class},
                            },
                        },
                        ElasticsearchQueryKeys.MODE: ElasticsearchQueryKeys.MAX,
                    },
                },
            ],
            ElasticsearchQueryKeys.SIZE: settings.MAX_ES_RESULTS_LONG,
        }

        response = await es.search(index=_build_index(series_name), body=query)
        hits = response[ElasticsearchKeys.HITS][ElasticsearchKeys.HITS]
        frames = [h[ElasticsearchKeys.SOURCE] for h in hits]
        await log_system_message(
            logging.INFO, f"Found {len(frames)} frames with object '{object_class}'.", logger,
        )
        return frames

    @staticmethod
    async def get_all_detected_objects(
        series_name: str,
        logger: logging.Logger,
    ) -> List[str]:
        await log_system_message(
            logging.INFO, f"Fetching all detected object classes for series '{series_name}'.", logger,
        )
        es = await ElasticSearchManager.connect_to_elasticsearch(logger)

        query = {
            ElasticsearchQueryKeys.SIZE: 0,
            ElasticsearchQueryKeys.AGGS: {
                _OBJECTS_AGG: {
                    ElasticsearchQueryKeys.NESTED: {ElasticsearchQueryKeys.PATH: VideoFrameKeys.DETECTED_OBJECTS},
                    ElasticsearchQueryKeys.AGGS: {
                        _CLASSES_AGG: {
                            ElasticsearchQueryKeys.TERMS: {
                                ElasticsearchQueryKeys.FIELD: _OBJECT_CLASS_FIELD,
                                ElasticsearchQueryKeys.SIZE: 500,
                                ElasticsearchQueryKeys.ORDER: {ElasticsearchQueryKeys.KEY: ElasticsearchQueryKeys.ASC},
                            },
                        },
                    },
                },
            },
        }

        response = await es.search(index=_build_index(series_name), body=query)
        buckets = response[ElasticsearchKeys.AGGREGATIONS][_OBJECTS_AGG][_CLASSES_AGG][ElasticsearchKeys.BUCKETS]
        classes = [b[ElasticsearchKeys.KEY] for b in buckets]
        await log_system_message(logging.INFO, f"Found {len(classes)} detected object classes.", logger)
        return classes


class CharacterFinder:
    @staticmethod
    def __character_field(subfield: str) -> str:
        return f"{ActorKeys.ACTORS}.{subfield}"

    @staticmethod
    def __season_0_term() -> Dict[str, Any]:
        return {ElasticsearchQueryKeys.TERM: {_SEASON_FIELD: 0}}

    @staticmethod
    def __char_term(character_name: str) -> Dict[str, Any]:
        return {
            ElasticsearchQueryKeys.TERM: {
                CharacterFinder.__character_field(ActorKeys.NAME): {
                    ElasticsearchQueryKeys.VALUE: character_name,
                    ElasticsearchQueryKeys.CASE_INSENSITIVE: True,
                },
            },
        }

    @staticmethod
    def __nested_char_filter(character_name: str) -> Dict[str, Any]:
        return {
            ElasticsearchQueryKeys.NESTED: {
                ElasticsearchQueryKeys.PATH: ActorKeys.ACTORS,
                ElasticsearchQueryKeys.QUERY: CharacterFinder.__char_term(character_name),
            },
        }

    @staticmethod
    def __parse_scene(source: Dict[str, Any], character_name: str) -> CharacterScene:
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

    @staticmethod
    def __confidence_sort(character_name: str) -> Dict[str, Any]:
        return {
            CharacterFinder.__character_field(ActorKeys.CONFIDENCE): {
                ElasticsearchQueryKeys.ORDER: ElasticsearchQueryKeys.DESC,
                ElasticsearchQueryKeys.NESTED: {
                    ElasticsearchQueryKeys.PATH: ActorKeys.ACTORS,
                    ElasticsearchQueryKeys.FILTER: CharacterFinder.__char_term(character_name),
                },
                ElasticsearchQueryKeys.MODE: ElasticsearchQueryKeys.MAX,
            },
        }

    @staticmethod
    def __emotion_confidence_sort(character_name: str, emotion_en: str) -> Dict[str, Any]:
        return {
            CharacterFinder.__character_field(f"{ActorKeys.EMOTION}.{EmotionKeys.CONFIDENCE}"): {
                ElasticsearchQueryKeys.ORDER: ElasticsearchQueryKeys.DESC,
                ElasticsearchQueryKeys.NESTED: {
                    ElasticsearchQueryKeys.PATH: ActorKeys.ACTORS,
                    ElasticsearchQueryKeys.FILTER: {
                        ElasticsearchQueryKeys.BOOL: {
                            ElasticsearchQueryKeys.MUST: [
                                CharacterFinder.__char_term(character_name),
                                {
                                    ElasticsearchQueryKeys.TERM: {
                                        CharacterFinder.__character_field(f"{ActorKeys.EMOTION}.{EmotionKeys.LABEL}"): emotion_en,
                                    },
                                },
                            ],
                        },
                    },
                },
                ElasticsearchQueryKeys.MODE: ElasticsearchQueryKeys.MAX,
            },
        }

    @staticmethod
    def __episode_sort() -> List[Dict[str, Any]]:
        return [
            {_SEASON_FIELD: ElasticsearchQueryKeys.ASC},
            {_EPISODE_FIELD: ElasticsearchQueryKeys.ASC},
            {VideoFrameKeys.TIMESTAMP: ElasticsearchQueryKeys.ASC},
        ]

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
                    ElasticsearchQueryKeys.MUST_NOT: [CharacterFinder.__season_0_term()],
                },
            },
            ElasticsearchQueryKeys.AGGS: {
                ElasticsearchAggregationKeys.ACTORS: {
                    ElasticsearchQueryKeys.NESTED: {ElasticsearchQueryKeys.PATH: ActorKeys.ACTORS},
                    ElasticsearchQueryKeys.AGGS: {
                        _NAMES_AGG: {
                            ElasticsearchQueryKeys.TERMS: {
                                ElasticsearchQueryKeys.FIELD: CharacterFinder.__character_field(ActorKeys.NAME),
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
        size: int = settings.MAX_ES_RESULTS_LONG,
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
                    ElasticsearchQueryKeys.FILTER: [CharacterFinder.__nested_char_filter(character_name)],
                    ElasticsearchQueryKeys.MUST_NOT: [CharacterFinder.__season_0_term()],
                },
            },
            ElasticsearchQueryKeys.SORT: [
                CharacterFinder.__confidence_sort(character_name),
                *CharacterFinder.__episode_sort(),
            ],
            ElasticsearchQueryKeys.SIZE: size,
        }

        response = await es.search(index=_build_index(series_name), body=query)
        hits = response[ElasticsearchKeys.HITS][ElasticsearchKeys.HITS]
        scenes = [CharacterFinder.__parse_scene(h[ElasticsearchKeys.SOURCE], character_name) for h in hits]
        await log_system_message(logging.INFO, f"Found {len(scenes)} scenes for '{character_name}'.", logger)
        return scenes

    @staticmethod
    async def get_scenes_by_character_and_emotion(
        character_name: str,
        emotion_en: str,
        series_name: str,
        logger: logging.Logger,
        size: int = settings.MAX_ES_RESULTS_LONG,
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
                            CharacterFinder.__char_term(character_name),
                            {
                                ElasticsearchQueryKeys.TERM: {
                                    CharacterFinder.__character_field(f"{ActorKeys.EMOTION}.{EmotionKeys.LABEL}"): emotion_en,
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
                    ElasticsearchQueryKeys.MUST_NOT: [CharacterFinder.__season_0_term()],
                },
            },
            ElasticsearchQueryKeys.SORT: [
                CharacterFinder.__emotion_confidence_sort(character_name, emotion_en),
                CharacterFinder.__confidence_sort(character_name),
                *CharacterFinder.__episode_sort(),
            ],
            ElasticsearchQueryKeys.SIZE: size,
        }

        response = await es.search(index=_build_index(series_name), body=query)
        hits = response[ElasticsearchKeys.HITS][ElasticsearchKeys.HITS]
        scenes = [CharacterFinder.__parse_scene(h[ElasticsearchKeys.SOURCE], character_name) for h in hits]
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
                                ElasticsearchQueryKeys.FIELD: CharacterFinder.__character_field(
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


class ObjectFinder:
    @staticmethod
    def __get_object_count(detected_objects: List[Dict[str, Any]], class_name: str) -> int:
        for obj in detected_objects:
            if obj.get(DetectedObjectKeys.CLASS, "").lower() == class_name.lower():
                return int(obj.get(DetectedObjectKeys.COUNT, 0))
        return 0

    @staticmethod
    def __group_frames_into_scenes(
        frames: List[Dict[str, Any]],
        class_name: str,
    ) -> List[ObjectScene]:
        scenes = {}
        for frame in frames:
            meta = frame.get(EpisodeMetadataKeys.EPISODE_METADATA, {})
            episode_id = frame.get(VideoFrameKeys.EPISODE_ID, "")
            scene_info = frame.get(VideoFrameKeys.SCENE_INFO) or {}
            scene_number = scene_info.get(SceneInfoKeys.SCENE_NUMBER)
            timestamp = frame.get(VideoFrameKeys.TIMESTAMP, 0.0)
            key = (
                episode_id,
                scene_number if scene_number is not None else timestamp,
            )

            count = ObjectFinder.__get_object_count(
                frame.get(VideoFrameKeys.DETECTED_OBJECTS, []),
                class_name,
            )

            if key not in scenes:
                scenes[key] = ObjectScene(
                    season=meta.get(EpisodeMetadataKeys.SEASON, 0),
                    episode_number=meta.get(EpisodeMetadataKeys.EPISODE_NUMBER, 0),
                    title=meta.get(EpisodeMetadataKeys.TITLE, ""),
                    start_time=scene_info.get(SceneInfoKeys.SCENE_START_TIME, timestamp),
                    end_time=scene_info.get(SceneInfoKeys.SCENE_END_TIME, timestamp),
                    total_count=0,
                    video_path=frame.get(SegmentKeys.VIDEO_PATH, ""),
                )
            scenes[key]["total_count"] += count

        return sorted(scenes.values(), key=lambda s: s["total_count"], reverse=True)

    @staticmethod
    def __clips_overlap(a: ObjectScene, b: ObjectScene) -> bool:
        a_start = a["start_time"] - settings.EXTEND_BEFORE
        a_end = a["end_time"] + settings.EXTEND_AFTER
        b_start = b["start_time"] - settings.EXTEND_BEFORE
        b_end = b["end_time"] + settings.EXTEND_AFTER
        return a_start <= b_end and b_start <= a_end

    @staticmethod
    def __deduplicate_by_fragment(scenes: List[ObjectScene]) -> List[ObjectScene]:
        result = []
        for scene in scenes:
            video_path = scene["video_path"]
            if not video_path:
                result.append(scene)
                continue
            already_covered = any(
                selected["video_path"] == video_path and ObjectFinder.__clips_overlap(scene, selected)
                for selected in result
            )
            if not already_covered:
                result.append(scene)
        return result

    @staticmethod
    async def get_all_objects(
        series_name: str,
        logger: logging.Logger,
    ) -> List[ObjectWithCount]:
        await log_system_message(
            logging.INFO, f"Fetching all object classes for series '{series_name}'.", logger,
        )
        es = await ElasticSearchManager.connect_to_elasticsearch(logger)

        query = {
            ElasticsearchQueryKeys.SIZE: 0,
            ElasticsearchQueryKeys.QUERY: {
                ElasticsearchQueryKeys.BOOL: {
                    ElasticsearchQueryKeys.MUST_NOT: [
                        {ElasticsearchQueryKeys.TERM: {_SEASON_FIELD: 0}},
                    ],
                },
            },
            ElasticsearchQueryKeys.AGGS: {
                _OBJECTS_AGG: {
                    ElasticsearchQueryKeys.NESTED: {
                        ElasticsearchQueryKeys.PATH: VideoFrameKeys.DETECTED_OBJECTS,
                    },
                    ElasticsearchQueryKeys.AGGS: {
                        _CLASSES_AGG: {
                            ElasticsearchQueryKeys.TERMS: {
                                ElasticsearchQueryKeys.FIELD: _OBJECT_CLASS_FIELD,
                                ElasticsearchQueryKeys.SIZE: 500,
                                ElasticsearchQueryKeys.ORDER: {
                                    ElasticsearchQueryKeys.KEY: ElasticsearchQueryKeys.ASC,
                                },
                            },
                            ElasticsearchQueryKeys.AGGS: {
                                _BACK_TO_ROOT: {
                                    ElasticsearchQueryKeys.REVERSE_NESTED: {},
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
            [_OBJECTS_AGG]
            [_CLASSES_AGG]
            [ElasticsearchKeys.BUCKETS]
        )
        objects = [
            ObjectWithCount(
                class_name=b[ElasticsearchKeys.KEY],
                scene_count=b[_BACK_TO_ROOT][_DOC_COUNT],
            )
            for b in buckets
        ]
        await log_system_message(logging.INFO, f"Found {len(objects)} object classes.", logger)
        return objects

    @staticmethod
    async def get_scenes_by_object(
        class_name: str,
        series_name: str,
        logger: logging.Logger,
    ) -> List[ObjectScene]:
        await log_system_message(
            logging.INFO, f"Fetching scenes for object '{class_name}' in series '{series_name}'.", logger,
        )
        frames = await VideoFramesFinder.find_frames_with_detected_object(
            object_class=class_name,
            series_name=series_name,
            logger=logger,
        )
        scenes = ObjectFinder.__group_frames_into_scenes(frames, class_name)
        scenes = ObjectFinder.__deduplicate_by_fragment(scenes)
        await log_system_message(
            logging.INFO, f"Found {len(scenes)} scenes for object '{class_name}'.", logger,
        )
        return scenes

    @staticmethod
    def apply_quantity_filter(
        scenes: List[ObjectScene],
        qty_filter: QuantityFilter,
    ) -> List[ObjectScene]:
        op = qty_filter["operator"]
        val = qty_filter["value"]
        predicate = _OPERATORS[op]
        return [s for s in scenes if predicate(s["total_count"], val)]

    @staticmethod
    async def find_best_matching_object(
        query: str,
        series_name: str,
        logger: logging.Logger,
    ) -> Optional[str]:
        all_classes = await VideoFramesFinder.get_all_detected_objects(series_name, logger)
        classes_lower = {c.lower(): c for c in all_classes}
        normalized = query.lower().strip()

        if normalized in classes_lower:
            return classes_lower[normalized]

        mapped = _OBJECT_NAMES.inverse.get(normalized)
        if mapped and mapped.lower() in classes_lower:
            return classes_lower[mapped.lower()]

        candidates = list(classes_lower.keys())
        matches = difflib.get_close_matches(normalized, candidates, n=1, cutoff=0.6)
        if matches:
            return classes_lower[matches[0]]

        polish_candidates = list(_OBJECT_NAMES.inverse.keys())
        polish_matches = difflib.get_close_matches(normalized, polish_candidates, n=1, cutoff=0.6)
        if polish_matches:
            mapped_from_fuzzy = _OBJECT_NAMES.inverse[polish_matches[0]]
            if mapped_from_fuzzy.lower() in classes_lower:
                return classes_lower[mapped_from_fuzzy.lower()]

        return None
