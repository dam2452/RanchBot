"""Load text segments for the chat's active /filtr (ES + visual post-filter)."""

from dataclasses import (
    dataclass,
    field,
)
from enum import Enum
import logging
from typing import (
    List,
    Optional,
    cast,
)

from bot.database.database_manager import DatabaseManager
from bot.search.filter_applicator import FilterApplicator
from bot.search.text_segments_finder import TextSegmentsFinder
from bot.types import (
    SearchFilter,
    SegmentWithScore,
)


class ActiveFilterTextSegmentsStatus(Enum):
    NO_FILTER = "no_filter"
    NO_CANDIDATES = "no_candidates"
    NO_MATCHES_POST_FILTER = "no_matches_post_filter"
    OK = "ok"


@dataclass
class ActiveFilterTextSegmentsOutcome:
    status: ActiveFilterTextSegmentsStatus
    search_filter: Optional[SearchFilter] = None
    segments: List[SegmentWithScore] = field(default_factory=list)


async def load_active_filter_text_segments(
        *,
        chat_id: int,
        series_name: str,
        logger: logging.Logger,
        es_query_size: int,
) -> ActiveFilterTextSegmentsOutcome:
    raw = await DatabaseManager.get_and_touch_user_filters(chat_id)
    if not raw:
        return ActiveFilterTextSegmentsOutcome(ActiveFilterTextSegmentsStatus.NO_FILTER)

    search_filter = cast(SearchFilter, raw)
    candidates = await TextSegmentsFinder.find_segments_by_filter_only(
        logger=logger,
        series_name=series_name,
        search_filter=search_filter,
        size=es_query_size,
    )
    if not candidates:
        return ActiveFilterTextSegmentsOutcome(
            ActiveFilterTextSegmentsStatus.NO_CANDIDATES,
            search_filter=search_filter,
        )

    filtered = await FilterApplicator.apply_to_text_segments(
        candidates, search_filter, series_name, logger,
    )
    if not filtered:
        return ActiveFilterTextSegmentsOutcome(
            ActiveFilterTextSegmentsStatus.NO_MATCHES_POST_FILTER,
            search_filter=search_filter,
        )

    return ActiveFilterTextSegmentsOutcome(
        ActiveFilterTextSegmentsStatus.OK,
        search_filter=search_filter,
        segments=list(filtered),
    )
