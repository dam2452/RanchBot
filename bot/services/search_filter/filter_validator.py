import logging
from typing import (
    List,
    Tuple,
)

from bot.responses.not_sending_videos.emotions_handler_responses import map_emotion_to_en
from bot.search.video_frames.character_finder import CharacterFinder
from bot.search.video_frames.object_finder import ObjectFinder
from bot.types import (
    ObjectFilterSpec,
    SearchFilter,
)


class FilterValidator:
    @staticmethod
    async def resolve(
        search_filter: SearchFilter,
        series_name: str,
        logger: logging.Logger,
    ) -> Tuple[SearchFilter, List[str]]:
        result = SearchFilter()

        if "seasons" in search_filter:
            result["seasons"] = search_filter["seasons"]
        if "episodes" in search_filter:
            result["episodes"] = search_filter["episodes"]
        if "episode_title" in search_filter:
            result["episode_title"] = search_filter["episode_title"]

        resolved_chars, char_messages = await FilterValidator.__resolve_character_groups(
            search_filter.get("character_groups", []), series_name, logger,
        )
        if resolved_chars:
            result["character_groups"] = resolved_chars

        resolved_emotions, emotion_messages = FilterValidator.__resolve_emotions(
            search_filter.get("emotions", []),
        )
        if resolved_emotions:
            result["emotions"] = resolved_emotions

        resolved_objects, object_messages = await FilterValidator.__resolve_object_groups(
            search_filter.get("object_groups", []), series_name, logger,
        )
        if resolved_objects:
            result["object_groups"] = resolved_objects

        return result, char_messages + emotion_messages + object_messages

    @staticmethod
    async def __resolve_character_groups(
        groups: List[List[str]],
        series_name: str,
        logger: logging.Logger,
    ) -> Tuple[List[List[str]], List[str]]:
        resolved_groups = []
        messages = []
        for group in groups:
            resolved_group = []
            for name in group:
                canonical = await CharacterFinder.find_best_matching_name(name, series_name, logger)
                if canonical is None:
                    messages.append(f"Nie znaleziono postaci '{name}' – pominięto.")
                else:
                    if canonical.lower() != name.lower():
                        messages.append(f"Postać '{name}' → '{canonical}'")
                    resolved_group.append(canonical)
            if resolved_group:
                resolved_groups.append(resolved_group)
        return resolved_groups, messages

    @staticmethod
    def __resolve_emotions(emotions: List[str]) -> Tuple[List[str], List[str]]:
        resolved = []
        messages = []
        for emotion in emotions:
            if map_emotion_to_en(emotion) is None:
                messages.append(f"Nieznana emocja '{emotion}' – pominięto.")
            else:
                resolved.append(emotion)
        return resolved, messages

    @staticmethod
    async def __resolve_object_groups(
        groups: List[List[ObjectFilterSpec]],
        series_name: str,
        logger: logging.Logger,
    ) -> Tuple[List[List[ObjectFilterSpec]], List[str]]:
        resolved_groups = []
        messages = []
        for group in groups:
            resolved_group = []
            for spec in group:
                canonical = await ObjectFinder.find_best_matching_object(spec["name"], series_name, logger)
                if canonical is None:
                    messages.append(f"Nie znaleziono obiektu '{spec['name']}' – pominięto.")
                else:
                    if canonical != spec["name"]:
                        messages.append(f"Obiekt '{spec['name']}' → '{canonical}'")
                    resolved_group.append(
                        ObjectFilterSpec(
                            name=canonical,
                            operator=spec.get("operator"),
                            value=spec.get("value"),
                        ),
                    )
            if resolved_group:
                resolved_groups.append(resolved_group)
        return resolved_groups, messages
