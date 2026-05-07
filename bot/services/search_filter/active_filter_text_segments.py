from dataclasses import (
    dataclass,
    field,
)
from enum import Enum
import logging
from typing import (
    List,
    Optional,
)

from bot.database.database_manager import DatabaseManager
from bot.search.infra.elastic_search_manager import ElasticSearchManager
from bot.search.scenes_finder import ScenesFinder
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

    search_filter: SearchFilter = raw

    es = await ElasticSearchManager.connect_to_elasticsearch(logger)
    segments = await ScenesFinder.find_by_filter(
        es=es,
        series_name=series_name,
        search_filter=search_filter,
        size=es_query_size,
        logger=logger,
    )

    if not segments:
        return ActiveFilterTextSegmentsOutcome(
            ActiveFilterTextSegmentsStatus.NO_CANDIDATES,
            search_filter=search_filter,
        )

    return ActiveFilterTextSegmentsOutcome(
        ActiveFilterTextSegmentsStatus.OK,
        search_filter=search_filter,
        segments=segments,
    )
