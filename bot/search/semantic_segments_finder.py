import logging
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from elasticsearch import NotFoundError

from bot.search.elastic_search_manager import ElasticSearchManager
from bot.search.vllm_client import VllmClient
from bot.settings import settings
from bot.utils.constants import (
    ElasticsearchKeys,
    EpisodeMetadataKeys,
    SegmentKeys,
)
from bot.utils.log import log_system_message


class SemanticSearchMode:
    TEXT = "tekst"
    FRAMES = "klatki"
    EPISODE = "odcinek"
    DEFAULT = TEXT

    _ALIASES: Dict[str, str] = {
        "t": TEXT, "tekst": TEXT, "text": TEXT,
        "k": FRAMES, "klatki": FRAMES, "frames": FRAMES,
        "o": EPISODE, "odcinek": EPISODE, "episode": EPISODE, "ep": EPISODE,
    }

    @classmethod
    def from_str(cls, token: str) -> Optional[str]:
        return cls._ALIASES.get(token.lower())


class SemanticSegmentsFinder:
    @staticmethod
    async def find_by_text(
        query: str,
        logger: logging.Logger,
        series_name: str,
        mode: str = SemanticSearchMode.DEFAULT,
        size: int = 999,
    ) -> Optional[List[Dict[str, Any]]]:
        await log_system_message(
            logging.INFO,
            f"Semantic search [{mode}] for '{query}' in series '{series_name}'.",
            logger,
        )
        embedding = await VllmClient.get_text_embedding(query, logger)

        if mode == SemanticSearchMode.FRAMES:
            return await SemanticSegmentsFinder._search_index(
                embedding=embedding,
                logger=logger,
                series_name=series_name,
                index_suffix=settings.ES_VIDEO_EMBEDDINGS_INDEX_SUFFIX,
                embedding_field="video_embedding",
                size=size,
            )
        if mode == SemanticSearchMode.EPISODE:
            return await SemanticSegmentsFinder._search_index(
                embedding=embedding,
                logger=logger,
                series_name=series_name,
                index_suffix=settings.ES_FULL_EPISODE_EMBEDDINGS_INDEX_SUFFIX,
                embedding_field="full_episode_embedding",
                size=size,
            )
        return await SemanticSegmentsFinder._search_index(
            embedding=embedding,
            logger=logger,
            series_name=series_name,
            index_suffix=settings.ES_TEXT_EMBEDDINGS_INDEX_SUFFIX,
            embedding_field="text_embedding",
            size=size,
        )

    @staticmethod
    async def _search_index(
        embedding: List[float],
        logger: logging.Logger,
        series_name: str,
        index_suffix: str,
        embedding_field: str,
        size: int,
    ) -> Optional[List[Dict[str, Any]]]:
        es = await ElasticSearchManager.connect_to_elasticsearch(logger)
        index = f"{series_name}_{index_suffix}"

        knn_query = {
            "knn": {
                "field": embedding_field,
                "query_vector": embedding,
                "k": size,
                "num_candidates": min(size * 10, 10000),
                "filter": [
                    {
                        "term": {
                            f"{EpisodeMetadataKeys.EPISODE_METADATA}"
                            f".{EpisodeMetadataKeys.SERIES_NAME}": series_name,
                        },
                    },
                ],
            },
        }

        try:
            response = await es.search(index=index, body=knn_query, size=size)
        except NotFoundError:
            await log_system_message(
                logging.WARNING,
                f"Embeddings index '{index}' not found.",
                logger,
            )
            return None

        hits = response[ElasticsearchKeys.HITS][ElasticsearchKeys.HITS]
        if not hits:
            await log_system_message(logging.INFO, "No semantic results found.", logger)
            return None

        results = []
        for hit in hits:
            doc: Dict[str, Any] = hit[ElasticsearchKeys.SOURCE]
            doc[ElasticsearchKeys.SCORE] = hit[ElasticsearchKeys.SCORE]
            results.append(doc)

        await log_system_message(
            logging.INFO,
            f"Semantic search [{index_suffix}] returned {len(results)} results.",
            logger,
        )
        return results

    @staticmethod
    def deduplicate_segments(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        unique = []
        for seg in segments:
            key = (
                seg.get(EpisodeMetadataKeys.EPISODE_METADATA, {}).get(EpisodeMetadataKeys.SEASON),
                seg.get(EpisodeMetadataKeys.EPISODE_METADATA, {}).get(EpisodeMetadataKeys.EPISODE_NUMBER),
                seg.get(SegmentKeys.START_TIME),
                seg.get(SegmentKeys.END_TIME),
            )
            if key not in seen:
                seen.add(key)
                unique.append(seg)
        return unique

    @staticmethod
    def deduplicate_frames(frames: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        unique = []
        for frame in frames:
            key = (
                frame.get(EpisodeMetadataKeys.EPISODE_METADATA, {}).get(EpisodeMetadataKeys.SEASON),
                frame.get(EpisodeMetadataKeys.EPISODE_METADATA, {}).get(EpisodeMetadataKeys.EPISODE_NUMBER),
                frame.get("frame_number"),
            )
            if key not in seen:
                seen.add(key)
                unique.append(frame)
        return unique

    @staticmethod
    def deduplicate_episodes(episodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        unique = []
        for ep in episodes:
            key = (
                ep.get(EpisodeMetadataKeys.EPISODE_METADATA, {}).get(EpisodeMetadataKeys.SEASON),
                ep.get(EpisodeMetadataKeys.EPISODE_METADATA, {}).get(EpisodeMetadataKeys.EPISODE_NUMBER),
            )
            if key not in seen:
                seen.add(key)
                unique.append(ep)
        return unique
