from dataclasses import (
    dataclass,
    field,
)
from enum import Enum
import logging
from typing import (
    Any,
    Dict,
    List,
    Optional,
    cast,
)

from bot.database.database_manager import DatabaseManager
from bot.responses.not_sending_videos.characters_handler_responses import scene_to_search_segment
from bot.responses.not_sending_videos.emotions_handler_responses import map_emotion_to_en
from bot.responses.not_sending_videos.objects_handler_responses import object_scene_to_search_segment
from bot.search.video_frames import (
    CharacterFinder,
    ObjectFinder,
)
from bot.types import (
    ObjectFilterSpec,
    QuantityFilter,
    SearchFilter,
)


class ActiveFilterSceneSegmentsStatus(Enum):
    NO_FILTER = "no_filter"
    NOT_SCENE_COMPATIBLE = "not_scene_compatible"
    NO_MATCHES = "no_matches"
    OK = "ok"


@dataclass
class ActiveFilterSceneSegmentsOutcome:
    status: ActiveFilterSceneSegmentsStatus
    search_filter: Optional[SearchFilter] = None
    segments: List[Dict[str, Any]] = field(default_factory=list)


def _is_scene_compatible(search_filter: SearchFilter) -> bool:
    character_groups = search_filter.get("character_groups") or []
    object_groups = search_filter.get("object_groups") or []
    emotions = search_filter.get("emotions") or []

    multi_char = len(character_groups) > 1 or any(len(g) > 1 for g in character_groups)
    multi_obj = len(object_groups) > 1 or any(len(g) > 1 for g in object_groups)
    multi_emotion = len(emotions) > 1
    char_present = bool(character_groups)
    obj_present = bool(object_groups)

    if multi_char or multi_obj or multi_emotion:
        return False
    if char_present and obj_present:
        return False
    if not char_present and not obj_present:
        return False
    return True


def _seasons_from_filter(search_filter: SearchFilter) -> Optional[List[int]]:
    seasons = search_filter.get("seasons")
    if seasons:
        return list(seasons)
    episodes = search_filter.get("episodes") or []
    season_set: set[int] = {
        cast(int, ep.get("season"))
        for ep in episodes
        if ep.get("season") is not None
    }
    return sorted(season_set) if season_set else None


async def _resolve_character_segments(
    search_filter: SearchFilter,
    series_name: str,
    logger: logging.Logger,
    size: int,
) -> List[Dict[str, Any]]:
    character = search_filter["character_groups"][0][0]
    seasons = _seasons_from_filter(search_filter)
    emotions = search_filter.get("emotions") or []
    emotion_en = map_emotion_to_en(emotions[0]) if emotions else None

    if emotion_en:
        scenes = await CharacterFinder.get_scenes_by_character_and_emotion(
            character_name=character,
            emotion_en=emotion_en,
            series_name=series_name,
            logger=logger,
            size=size,
            seasons=seasons,
        )
    else:
        scenes = await CharacterFinder.get_scenes_by_character(
            character_name=character,
            series_name=series_name,
            logger=logger,
            size=size,
            seasons=seasons,
        )
    return [scene_to_search_segment(scene) for scene in scenes]


async def _resolve_object_segments(
    search_filter: SearchFilter,
    series_name: str,
    logger: logging.Logger,
    size: int,
) -> List[Dict[str, Any]]:
    obj_spec = cast(ObjectFilterSpec, search_filter["object_groups"][0][0])
    seasons = _seasons_from_filter(search_filter)

    scenes = await ObjectFinder.get_scenes_by_object(
        class_name=obj_spec["name"],
        series_name=series_name,
        logger=logger,
        seasons=seasons,
    )
    if obj_spec.get("operator") is not None and obj_spec.get("value") is not None:
        qty_filter: QuantityFilter = {
            "operator": cast(str, obj_spec["operator"]),
            "value": cast(int, obj_spec["value"]),
        }
        scenes = ObjectFinder.apply_quantity_filter(scenes, qty_filter)
    return [object_scene_to_search_segment(scene) for scene in scenes[:size]]


async def load_active_filter_scene_segments(
    *,
    chat_id: int,
    series_name: str,
    logger: logging.Logger,
    size: int,
) -> ActiveFilterSceneSegmentsOutcome:
    raw = await DatabaseManager.get_and_touch_user_filters(chat_id)
    if not raw:
        return ActiveFilterSceneSegmentsOutcome(ActiveFilterSceneSegmentsStatus.NO_FILTER)

    search_filter = cast(SearchFilter, raw)
    if not _is_scene_compatible(search_filter):
        return ActiveFilterSceneSegmentsOutcome(
            ActiveFilterSceneSegmentsStatus.NOT_SCENE_COMPATIBLE,
            search_filter=search_filter,
        )

    if search_filter.get("character_groups"):
        segments = await _resolve_character_segments(search_filter, series_name, logger, size)
    else:
        segments = await _resolve_object_segments(search_filter, series_name, logger, size)

    if not segments:
        return ActiveFilterSceneSegmentsOutcome(
            ActiveFilterSceneSegmentsStatus.NO_MATCHES,
            search_filter=search_filter,
        )

    return ActiveFilterSceneSegmentsOutcome(
        ActiveFilterSceneSegmentsStatus.OK,
        search_filter=search_filter,
        segments=segments,
    )
