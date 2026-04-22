from enum import Enum
import logging
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
)

from elasticsearch import NotFoundError

from bot.search.infra.elastic_search_manager import ElasticSearchManager
from bot.search.infra.vllm_client import VllmClient
from bot.settings import settings
from bot.utils.constants import (
    ActorKeys,
    ElasticsearchIndexSuffixes,
    ElasticsearchKeys,
    ElasticsearchQueryKeys,
    EmbeddingKeys,
    EpisodeMetadataKeys,
    SegmentKeys,
    VideoFrameKeys,
)
from bot.utils.log import log_system_message


class SemanticSearchMode(str, Enum):
    TEXT = "tekst"
    FRAMES = "klatki"
    EPISODE = "odcinek"
    DEFAULT = "tekst"

    __ALIASES = {
        "t": "tekst", "text": "tekst",
        "k": "klatki", "frames": "klatki",
        "o": "odcinek", "episode": "odcinek", "ep": "odcinek",
    }

    @classmethod
    def _missing_(cls, value: object) -> Optional["SemanticSearchMode"]:
        mapped = cls.__ALIASES.get(str(value).lower())  # pylint: disable=no-member
        return cls(mapped) if mapped else None

    @classmethod
    def from_str(cls, token: str) -> Optional["SemanticSearchMode"]:
        try:
            return cls(token.lower())
        except ValueError:
            return None


class SemanticSegmentsFinder:
    __SOURCE_FIELDS_BY_SUFFIX = {
        settings.ES_TEXT_EMBEDDINGS_INDEX_SUFFIX: [
            EmbeddingKeys.EPISODE_ID,
            EpisodeMetadataKeys.EPISODE_METADATA,
            EmbeddingKeys.EMBEDDING_ID,
            SegmentKeys.SEGMENT_ID,
            EmbeddingKeys.SEGMENT_RANGE,
            SegmentKeys.TEXT,
            SegmentKeys.START_TIME,
            SegmentKeys.END_TIME,
            SegmentKeys.VIDEO_PATH,
        ],
        settings.ES_VIDEO_EMBEDDINGS_INDEX_SUFFIX: [
            EmbeddingKeys.EPISODE_ID,
            EpisodeMetadataKeys.EPISODE_METADATA,
            EmbeddingKeys.FRAME_NUMBER,
            VideoFrameKeys.TIMESTAMP,
            VideoFrameKeys.FRAME_TYPE,
            VideoFrameKeys.SCENE_NUMBER,
            SegmentKeys.VIDEO_PATH,
            VideoFrameKeys.SCENE_INFO,
            ActorKeys.ACTORS,
            VideoFrameKeys.DETECTED_OBJECTS,
        ],
        settings.ES_FULL_EPISODE_EMBEDDINGS_INDEX_SUFFIX: [
            EmbeddingKeys.EPISODE_ID,
            EpisodeMetadataKeys.EPISODE_METADATA,
            EmbeddingKeys.FULL_TRANSCRIPT,
        ],
    }

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
            frames = await SemanticSegmentsFinder.__search_index(
                embedding=embedding,
                logger=logger,
                series_name=series_name,
                index_suffix=settings.ES_VIDEO_EMBEDDINGS_INDEX_SUFFIX,
                embedding_field=EmbeddingKeys.VIDEO_EMBEDDING,
                size=size,
            )
            return SemanticSegmentsFinder.__normalize_frames(frames) if frames is not None else None
        if mode == SemanticSearchMode.EPISODE:
            return await SemanticSegmentsFinder.__search_index(
                embedding=embedding,
                logger=logger,
                series_name=series_name,
                index_suffix=settings.ES_FULL_EPISODE_EMBEDDINGS_INDEX_SUFFIX,
                embedding_field=EmbeddingKeys.FULL_EPISODE_EMBEDDING,
                size=size,
            )
        segments = await SemanticSegmentsFinder.__search_index(
            embedding=embedding,
            logger=logger,
            series_name=series_name,
            index_suffix=settings.ES_TEXT_EMBEDDINGS_INDEX_SUFFIX,
            embedding_field=EmbeddingKeys.TEXT_EMBEDDING,
            size=size,
        )
        if segments is not None:
            await SemanticSegmentsFinder.__normalize_text_segments(segments, series_name, logger)
        return segments

    @staticmethod
    async def __normalize_text_segments(
        segments: List[Dict[str, Any]],
        series_name: str,
        logger: logging.Logger,
    ) -> None:
        episode_to_seg_ids: Dict[str, Set[int]] = {}
        for seg in segments:
            episode_id = seg.get(EmbeddingKeys.EPISODE_ID, "")
            seg_range = seg.get(EmbeddingKeys.SEGMENT_RANGE, [])
            if not episode_id or len(seg_range) < 2:
                continue
            episode_to_seg_ids.setdefault(episode_id, set()).update({seg_range[0], seg_range[-1]})

        es = await ElasticSearchManager.connect_to_elasticsearch(logger)
        index = f"{series_name}{ElasticsearchIndexSuffixes.TEXT_SEGMENTS}"
        lookup: Dict[Tuple[str, int], Dict[str, Any]] = {}
        if episode_to_seg_ids:
            should_filters = [
                {
                    "bool": {
                        ElasticsearchQueryKeys.FILTER: [
                            {ElasticsearchQueryKeys.TERM: {EmbeddingKeys.EPISODE_ID: episode_id}},
                            {ElasticsearchQueryKeys.TERMS: {SegmentKeys.SEGMENT_ID: list(seg_ids)}},
                        ],
                    },
                }
                for episode_id, seg_ids in episode_to_seg_ids.items()
            ]
            max_hits = sum(len(seg_ids) for seg_ids in episode_to_seg_ids.values())
            query = {
                ElasticsearchQueryKeys.QUERY: {
                    ElasticsearchQueryKeys.BOOL: {
                        ElasticsearchQueryKeys.SHOULD: should_filters,
                        ElasticsearchQueryKeys.MINIMUM_SHOULD_MATCH: 1,
                    },
                },
                ElasticsearchQueryKeys.SIZE: max(1, max_hits),
                ElasticsearchQueryKeys.SOURCE: [
                    EmbeddingKeys.EPISODE_ID,
                    SegmentKeys.SEGMENT_ID,
                    SegmentKeys.START_TIME,
                    SegmentKeys.END_TIME,
                    SegmentKeys.VIDEO_PATH,
                ],
            }
            response = await es.search(index=index, body=query)
            for hit in response[ElasticsearchKeys.HITS][ElasticsearchKeys.HITS]:
                src = hit[ElasticsearchKeys.SOURCE]
                lookup[(src[EmbeddingKeys.EPISODE_ID], src[SegmentKeys.SEGMENT_ID])] = src

        for seg in segments:
            episode_id = seg.get(EmbeddingKeys.EPISODE_ID, "")
            seg_range = seg.get(EmbeddingKeys.SEGMENT_RANGE, [])
            if not episode_id or len(seg_range) < 2:
                continue
            start_data = lookup.get((episode_id, seg_range[0]))
            end_data = lookup.get((episode_id, seg_range[-1]))
            if start_data:
                seg[SegmentKeys.START_TIME] = start_data[SegmentKeys.START_TIME]
                seg[SegmentKeys.VIDEO_PATH] = start_data.get(SegmentKeys.VIDEO_PATH, "")
            if end_data:
                seg[SegmentKeys.END_TIME] = end_data[SegmentKeys.END_TIME]

    @staticmethod
    async def __search_index(
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
                ElasticsearchQueryKeys.FIELD: embedding_field,
                "query_vector": embedding,
                "k": size,
                "num_candidates": min(size * 10, 10000),
            },
            ElasticsearchQueryKeys.SOURCE: SemanticSegmentsFinder.__SOURCE_FIELDS_BY_SUFFIX.get(index_suffix, True),
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
    def __normalize_frames(frames: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        for frame in frames:
            scene = frame.get(VideoFrameKeys.SCENE_INFO, {})
            timestamp = frame.get(VideoFrameKeys.TIMESTAMP, 0.0)
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
                frame.get(VideoFrameKeys.SCENE_NUMBER),
            )
            if key not in seen:
                seen.add(key)
                unique.append(frame)
        return unique

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
