import re
import shlex
from typing import (
    List,
    Optional,
    Tuple,
)

from bot.services.search_filter.filter_schema import alias_to_canonical
from bot.types import (
    EpisodeSpec,
    ObjectFilterSpec,
    SearchFilter,
)


class FilterParser:
    __SXXEXX_PATTERN = re.compile(r"^[Ss](\d+)[Ee](\d+)$")
    __QUANTITY_SUFFIX_PATTERN = re.compile(r"^(.+?)(>=|<=|>|<|=)(\d+)$")

    def parse(self, raw: str) -> Tuple[Optional[SearchFilter], List[str]]:
        errors = []
        result = SearchFilter()

        try:
            tokens = shlex.split(raw)
        except ValueError as e:
            return None, [f"Błąd parsowania: {e}"]

        character_groups = []
        emotions = []
        object_groups = []

        for token in tokens:
            if ":" not in token:
                errors.append(f"Nieprawidłowy token: '{token}' (oczekiwany format klucz:wartość)")
                continue
            key, _, value = token.partition(":")
            key = key.lower().strip()
            value = value.strip()
            if not value:
                errors.append(f"Brak wartości dla klucza '{key}'")
                continue
            self.__process_token(key, value, result, character_groups, emotions, object_groups, errors)

        if character_groups:
            result["character_groups"] = character_groups
        if emotions:
            result["emotions"] = emotions
        if object_groups:
            result["object_groups"] = object_groups

        return result, errors

    def __process_token(
        self,
        key: str,
        value: str,
        result: SearchFilter,
        character_groups: List[List[str]],
        emotions: List[str],
        object_groups: List[List[ObjectFilterSpec]],
        errors: List[str],
    ) -> None:
        canonical = alias_to_canonical(key)
        if canonical is None:
            errors.append(f"Nieznany filtr: '{key}'")
            return

        if canonical == "sezon":
            parsed = self._parse_seasons(value)
            if parsed is None:
                errors.append(f"Nieprawidłowy format sezonu: '{value}'")
            else:
                result["seasons"] = parsed

        elif canonical == "odcinek":
            parsed_eps = self._parse_episodes(value)
            if parsed_eps is None:
                errors.append(f"Nieprawidłowy format odcinka: '{value}'")
            else:
                result["episodes"] = parsed_eps

        elif canonical == "tytul":
            result["episode_title"] = value

        elif canonical == "postac":
            names = [n.strip() for n in value.split(",") if n.strip()]
            if names:
                character_groups.append(names)

        elif canonical == "emocja":
            emotions.extend(e.strip() for e in value.split(",") if e.strip())

        elif canonical == "obiekt":
            group = self._parse_object_group(value)
            if group is None:
                errors.append(f"Nieprawidłowy format obiektu: '{value}'")
            else:
                object_groups.append(group)

    def _parse_seasons(self, value: str) -> Optional[List[int]]:
        if "-" in value and "," not in value:
            parts = value.split("-", 1)
            if not parts[0].isdigit() or not parts[1].isdigit():
                return None
            start, end = int(parts[0]), int(parts[1])
            if start > end:
                return None
            return list(range(start, end + 1))

        parts = value.split(",")
        seasons = []
        for part in parts:
            part = part.strip()
            if not part.isdigit():
                return None
            seasons.append(int(part))
        return seasons if seasons else None

    def _parse_episodes(self, value: str) -> Optional[List[EpisodeSpec]]:
        if "," in value:
            specs = []
            for item in value.split(","):
                spec = self.__parse_single_episode(item.strip())
                if spec is None:
                    return None
                specs.append(spec)
            return specs if specs else None

        if "-" in value:
            parts = value.split("-", 1)
            m0 = self.__SXXEXX_PATTERN.match(parts[0])
            m1 = self.__SXXEXX_PATTERN.match(parts[1])
            if m0 and m1:
                s0, e0 = int(m0.group(1)), int(m0.group(2))
                s1, e1 = int(m1.group(1)), int(m1.group(2))
                if s0 != s1:
                    return None
                return [EpisodeSpec(season=s0, episode=ep) for ep in range(e0, e1 + 1)]
            if parts[0].isdigit() and parts[1].isdigit():
                e0, e1 = int(parts[0]), int(parts[1])
                return [EpisodeSpec(season=None, episode=ep) for ep in range(e0, e1 + 1)]
            return None

        spec = self.__parse_single_episode(value)
        return [spec] if spec is not None else None

    def __parse_single_episode(self, value: str) -> Optional[EpisodeSpec]:
        m = self.__SXXEXX_PATTERN.match(value)
        if m:
            return EpisodeSpec(season=int(m.group(1)), episode=int(m.group(2)))
        if value.isdigit():
            return EpisodeSpec(season=None, episode=int(value))
        return None

    def _parse_object_group(self, value: str) -> Optional[List[ObjectFilterSpec]]:
        items = [v.strip() for v in value.split(",") if v.strip()]
        group = []
        for item in items:
            m = self.__QUANTITY_SUFFIX_PATTERN.match(item)
            if m:
                group.append(ObjectFilterSpec(name=m.group(1).strip(), operator=m.group(2), value=int(m.group(3))))
            else:
                group.append(ObjectFilterSpec(name=item, operator=None, value=None))
        return group if group else None
