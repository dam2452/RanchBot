import logging
from typing import (
    Any,
    Dict,
    List,
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
            meta = frame.get(EpisodeMetadataKeys.EPISODE_METADATA, {})
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
                                ElasticsearchQueryKeys.ORDER: {"_count": ElasticsearchQueryKeys.DESC},
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
            ObjectWithCount(class_name=b[ElasticsearchKeys.KEY], frame_count=b[_DOC_COUNT])
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
