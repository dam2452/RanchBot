from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from preprocessor.cli.search_handler import SearchFilters


@dataclass
class SearchQueryParams:

    text: Optional[str] = None
    text_semantic: Optional[str] = None
    text_to_video: Optional[str] = None
    image: Optional[Path] = None
    phash: Optional[str] = None
    character: Optional[str] = None
    emotion: Optional[str] = None
    object_query: Optional[str] = None
    episode_name: Optional[str] = None
    episode_name_semantic: Optional[str] = None

    def has_search_criteria(self) -> bool:
        return any([
            self.text,
            self.text_semantic,
            self.text_to_video,
            self.image,
            self.phash,
            self.character,
            self.emotion,
            self.object_query,
            self.episode_name,
            self.episode_name_semantic,
        ])


@dataclass
class SearchActionParams:

    list_chars_flag: bool = False
    list_objects_flag: bool = False
    stats: bool = False

    def has_action(self) -> bool:
        return any([
            self.list_chars_flag,
            self.list_objects_flag,
            self.stats,
        ])


@dataclass
class SearchConfig:

    series: str
    query: SearchQueryParams
    filters: SearchFilters
    actions: SearchActionParams
    json_output: bool = False
    host: str = "http://localhost:9200"

    def has_any_operation(self) -> bool:
        return self.query.has_search_criteria() or self.actions.has_action()
