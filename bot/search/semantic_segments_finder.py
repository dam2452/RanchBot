from enum import Enum
import logging
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Set,
)

from elasticsearch import NotFoundError

from bot.search.infra.elastic_search_manager import ElasticSearchManager
from bot.search.infra.vllm_client import VllmClient
from bot.settings import settings
from bot.utils.constants import (
    ElasticsearchIndexSuffixes,
    ElasticsearchKeys,
    EpisodeMetadataKeys,
    SegmentKeys,
)
from bot.utils.log import log_system_message


class SemanticSearchMode(str, Enum):
    TEXT = "tekst"
    FRAMES = "klatki"
    EPISODE = "odcinek"
    DEFAULT = "tekst"

    @classmethod
    def _missing_(cls, value: object) -> Optional["SemanticSearchMode"]:
        return _SEMANTIC_MODE_ALIASES.get(str(value).lower())

    @classmethod
    def from_str(cls, token: str) -> Optional["SemanticSearchMode"]:
        try:
            return cls(token.lower())
        except ValueError:
            return None


_SEMANTIC_MODE_ALIASES: Dict[str, SemanticSearchMode] = {
    "t": SemanticSearchMode.TEXT, "text": SemanticSearchMode.TEXT,
    "k": SemanticSearchMode.FRAMES, "frames": SemanticSearchMode.FRAMES,
    "o": SemanticSearchMode.EPISODE, "episode": SemanticSearchMode.EPISODE, "ep": SemanticSearchMode.EPISODE,
}


class SemanticSegmentsFinder:
    @staticmethod
    async def find_by_text(
        query: str,
        logger: logging.Logger,
        series_name: str,
        mode: "SemanticSearchMode" = SemanticSearchMode.DEFAULT,
        size: int = settings.MAX_ES_RESULTS_LONG,
    ) -> Optional[List[Dict[str, Any]]]:
        await log_system_message(
            logging.INFO,
            f"Semantic search [{mode}] for '{query}' in series '{series_name}'.",
            logger,
        )
        embedding = await VllmClient.get_text_embedding(query, logger)

        if mode == SemanticSearchMode.FRAMES:
            frames = await SemanticSegmentsFinder._search_index(
                embedding=embedding,
                logger=logger,
                series_name=series_name,
                index_suffix=settings.ES_VIDEO_EMBEDDINGS_INDEX_SUFFIX,
                embedding_field="video_embedding",
                size=size,
            )
            return SemanticSegmentsFinder.__normalize_frames(frames) if frames is not None else None
        if mode == SemanticSearchMode.EPISODE:
            return await SemanticSegmentsFinder._search_index(
                embedding=embedding,
                logger=logger,
                series_name=series_name,
                index_suffix=settings.ES_FULL_EPISODE_EMBEDDINGS_INDEX_SUFFIX,
                embedding_field="full_episode_embedding",
                size=size,
            )
        segments = await SemanticSegmentsFinder._search_index(
            embedding=embedding,
            logger=logger,
            series_name=series_name,
            index_suffix=settings.ES_TEXT_EMBEDDINGS_INDEX_SUFFIX,
            embedding_field="text_embedding",
            size=size,
        )
        if segments is not None:
            await SemanticSegmentsFinder._normalize_text_segments(segments, series_name, logger)
        return segments

    @staticmethod
    async def _normalize_text_segments(
        segments: List[Dict[str, Any]],
        series_name: str,
        logger: logging.Logger,
    ) -> None:
        episode_to_seg_ids: Dict[str, Set[int]] = {}
        for seg in segments:
            episode_id = seg.get("episode_id", "")
            seg_range = seg.get("segment_range", [])
            if not episode_id or len(seg_range) < 2:
                continue
            episode_to_seg_ids.setdefault(episode_id, set()).update({seg_range[0], seg_range[-1]})

        es = await ElasticSearchManager.connect_to_elasticsearch(logger)
        index = f"{series_name}{ElasticsearchIndexSuffixes.TEXT_SEGMENTS}"
        lookup = {}

        for episode_id, seg_ids in episode_to_seg_ids.items():
            query = {
                "query": {
                    "bool": {
                        "filter": [
                            {"term": {"episode_id": episode_id}},
                            {"terms": {"segment_id": list(seg_ids)}},
                        ],
                    },
                },
                "size": len(seg_ids) * 2,
                "_source": ["segment_id", "start_time", "end_time", "video_path"],
            }
            try:
                response = await es.search(index=index, body=query)
                for hit in response["hits"]["hits"]:
                    src = hit["_source"]
                    lookup[(episode_id, src["segment_id"])] = src
            except Exception:  # pylint: disable=broad-except
                pass

        for seg in segments:
            episode_id = seg.get("episode_id", "")
            seg_range = seg.get("segment_range", [])
            if not episode_id or len(seg_range) < 2:
                continue
            start_data = lookup.get((episode_id, seg_range[0]))
            end_data = lookup.get((episode_id, seg_range[-1]))
            if start_data:
                seg[SegmentKeys.START_TIME] = start_data["start_time"]
                seg[SegmentKeys.VIDEO_PATH] = start_data.get("video_path", "")
            if end_data:
                seg[SegmentKeys.END_TIME] = end_data["end_time"]

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
    def __normalize_frames(frames: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        for frame in frames:
            scene = frame.get("scene_info", {})
            timestamp = frame.get("timestamp", 0.0)
            frame[SegmentKeys.START_TIME] = scene.get("scene_start_time", timestamp)
            frame[SegmentKeys.END_TIME] = scene.get("scene_end_time", timestamp)
        return frames

    @staticmethod
    def deduplicate_frames(frames: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        unique = []
        for frame in frames:
            key = (
                frame.get(EpisodeMetadataKeys.EPISODE_METADATA, {}).get(EpisodeMetadataKeys.SEASON),
                frame.get(EpisodeMetadataKeys.EPISODE_METADATA, {}).get(EpisodeMetadataKeys.EPISODE_NUMBER),
                frame.get("scene_number"),
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
