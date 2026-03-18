import difflib
import logging
from typing import (
    List,
    Optional,
)

from bidict import bidict

from bot.search.infra.elastic_search_manager import ElasticSearchManager
from bot.search.video_frames.frames_finder import (
    VideoFramesFinder,
    _build_index,
)
from bot.settings import settings
from bot.types import (
    DetectedObjectSource,
    ObjectScene,
    ObjectWithCount,
    QuantityFilter,
    VideoFrameSource,
)
from bot.utils.constants import (
    DetectedObjectKeys,
    ElasticsearchAggregationKeys,
    ElasticsearchKeys,
    ElasticsearchQueryKeys,
    EpisodeMetadataKeys,
    SceneInfoKeys,
    SegmentKeys,
    VideoFrameKeys,
)
from bot.utils.log import log_system_message

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


def get_polish_name(class_name: str) -> str:
    return _OBJECT_NAMES.get(class_name.lower(), class_name)


class ObjectFinder:
    @staticmethod
    def __get_object_count(detected_objects: List[DetectedObjectSource], class_name: str) -> int:
        for obj in detected_objects:
            if obj.get(DetectedObjectKeys.CLASS, "").lower() == class_name.lower():
                return int(obj.get(DetectedObjectKeys.COUNT, 0))
        return 0

    @staticmethod
    def __group_frames_into_scenes(
        frames: List[VideoFrameSource],
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
    async def get_all_objects(  # pylint: disable=duplicate-code
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
                        {ElasticsearchQueryKeys.TERM: {EpisodeMetadataKeys.SEASON_FIELD: 0}},
                    ],
                },
            },
            ElasticsearchQueryKeys.AGGS: {
                ElasticsearchAggregationKeys.OBJECTS: {
                    ElasticsearchQueryKeys.NESTED: {
                        ElasticsearchQueryKeys.PATH: VideoFrameKeys.DETECTED_OBJECTS,
                    },
                    ElasticsearchQueryKeys.AGGS: {
                        ElasticsearchAggregationKeys.CLASSES: {
                            ElasticsearchQueryKeys.TERMS: {
                                ElasticsearchQueryKeys.FIELD: DetectedObjectKeys.OBJECT_CLASS_FIELD,
                                ElasticsearchQueryKeys.SIZE: 500,
                                ElasticsearchQueryKeys.ORDER: {
                                    ElasticsearchQueryKeys.KEY: ElasticsearchQueryKeys.ASC,
                                },
                            },
                            ElasticsearchQueryKeys.AGGS: {
                                ElasticsearchAggregationKeys.BACK_TO_ROOT: {
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
            [ElasticsearchAggregationKeys.OBJECTS]
            [ElasticsearchAggregationKeys.CLASSES]
            [ElasticsearchKeys.BUCKETS]
        )
        objects = [
            ObjectWithCount(
                class_name=b[ElasticsearchKeys.KEY],
                scene_count=b[ElasticsearchAggregationKeys.BACK_TO_ROOT][ElasticsearchKeys.DOC_COUNT],
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
        seasons: Optional[List[int]] = None,
    ) -> List[ObjectScene]:
        await log_system_message(
            logging.INFO, f"Fetching scenes for object '{class_name}' in series '{series_name}'.", logger,
        )
        frames = await VideoFramesFinder.find_frames_with_detected_object(
            object_class=class_name,
            series_name=series_name,
            logger=logger,
            seasons=seasons,
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
