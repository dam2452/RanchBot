import difflib
import logging
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from bot.search.elastic_search_manager import ElasticSearchManager
from bot.search.video_frames_finder import VideoFramesFinder
from bot.types import (
    ObjectScene,
    ObjectWithCount,
    QuantityFilter,
)
from bot.utils.constants import (
    DetectedObjectKeys,
    ElasticsearchIndexSuffixes,
    ElasticsearchKeys,
    ElasticsearchQueryKeys,
    EpisodeMetadataKeys,
    SceneInfoKeys,
    SegmentKeys,
    VideoFrameKeys,
)
from bot.utils.log import log_system_message

_OBJECT_CLASS_FIELD = f"{VideoFrameKeys.DETECTED_OBJECTS}.{DetectedObjectKeys.CLASS}"
_SEASON_FIELD = f"{EpisodeMetadataKeys.EPISODE_METADATA}.{EpisodeMetadataKeys.SEASON}"
_OBJECTS_AGG = "objects"
_CLASSES_AGG = "classes"
_BACK_TO_ROOT = "back_to_root"
_DOC_COUNT = "doc_count"

_OPERATORS = {
    "=": lambda c, v: c == v,
    ">": lambda c, v: c > v,
    "<": lambda c, v: c < v,
    ">=": lambda c, v: c >= v,
    "<=": lambda c, v: c <= v,
}

_POLISH_TO_ENGLISH: Dict[str, str] = {
    "osoba": "person",
    "człowiek": "person",
    "ludzie": "person",
    "rower": "bicycle",
    "samochód": "car",
    "auto": "car",
    "pojazd": "car",
    "motocykl": "motorbike",
    "motor": "motorbike",
    "samolot": "aeroplane",
    "autobus": "bus",
    "pociąg": "train",
    "ciężarówka": "truck",
    "łódź": "boat",
    "koń": "horse",
    "krowa": "cow",
    "owca": "sheep",
    "pies": "dog",
    "kot": "cat",
    "ptak": "bird",
    "krzesło": "chair",
    "sofa": "sofa",
    "kanapa": "sofa",
    "stół": "diningtable",
    "stolik": "diningtable",
    "telewizor": "tvmonitor",
    "laptop": "laptop",
    "telefon": "cell phone",
    "komórka": "cell phone",
    "butelka": "bottle",
    "kubek": "cup",
    "szklanka": "cup",
    "talerz": "bowl",
    "miska": "bowl",
    "nóż": "knife",
    "widelec": "fork",
    "łyżka": "spoon",
    "plecak": "backpack",
    "torba": "handbag",
    "walizka": "suitcase",
    "zegar": "clock",
    "książka": "book",
    "wazon": "vase",
    "krawat": "tie",
    "parasol": "umbrella",
    "jabłko": "apple",
    "banan": "banana",
    "marchew": "carrot",
    "pomarańcza": "orange",
    "pizza": "pizza",
    "kanapka": "sandwich",
    "ciasto": "cake",
    "pączek": "donut",
    "brokuł": "broccoli",
    "hot dog": "hot dog",
    "kieliszek": "wine glass",
    "nożyczki": "scissors",
    "szczoteczka": "toothbrush",
    "szczoteczka do zębów": "toothbrush",
    "klawiatura": "keyboard",
    "myszka": "mouse",
    "pilot": "remote",
    "lodówka": "refrigerator",
    "kuchenka": "microwave",
    "mikrofalówka": "microwave",
    "piekarnik": "oven",
    "toster": "toaster",
    "zlew": "sink",
    "toaleta": "toilet",
    "łóżko": "bed",
    "ławka": "bench",
    "niedźwiedź": "bear",
    "słoń": "elephant",
    "żyrafa": "giraffe",
    "miś": "teddy bear",
    "latawiec": "kite",
    "narta": "skis",
    "narty": "skis",
    "deskorolka": "skateboard",
    "deska": "surfboard",
    "rakieta": "tennis racket",
    "frisbee": "frisbee",
    "piłka": "sports ball",
    "hydrant": "fire hydrant",
    "parkometr": "parking meter",
    "znak stop": "stop sign",
    "sygnalizacja": "traffic light",
    "roślina": "pottedplant",
    "doniczka": "pottedplant",
    "suszarka": "hair drier",
}

_ENGLISH_TO_POLISH: Dict[str, str] = {
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
}


def get_polish_name(class_name: str) -> str:
    return _ENGLISH_TO_POLISH.get(class_name.lower(), class_name)


def _build_index(series_name: str) -> str:
    return f"{series_name}{ElasticsearchIndexSuffixes.VIDEO_FRAMES}"


def _get_object_count(detected_objects: List[Dict[str, Any]], class_name: str) -> int:
    for obj in detected_objects:
        if obj.get(DetectedObjectKeys.CLASS, "").lower() == class_name.lower():
            return int(obj.get(DetectedObjectKeys.COUNT, 0))
    return 0


def _group_frames_into_scenes(
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

        count = _get_object_count(
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


class ObjectFinder:
    @staticmethod
    async def get_all_objects(
        series_name: str,
        logger: logging.Logger,
    ) -> List[ObjectWithCount]:
        await log_system_message(
            logging.INFO, f"Fetching all object classes for series '{series_name}'.", logger,
        )
        es = await ElasticSearchManager.connect_to_elasticsearch(logger)

        query: Dict[str, Any] = {
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
        scenes = _group_frames_into_scenes(frames, class_name)
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

        mapped = _POLISH_TO_ENGLISH.get(normalized)
        if mapped and mapped.lower() in classes_lower:
            return classes_lower[mapped.lower()]

        candidates = list(classes_lower.keys())
        matches = difflib.get_close_matches(normalized, candidates, n=1, cutoff=0.6)
        if matches:
            return classes_lower[matches[0]]

        if mapped:
            matches = difflib.get_close_matches(mapped.lower(), candidates, n=1, cutoff=0.6)
            if matches:
                return classes_lower[matches[0]]

        return None
