from dataclasses import dataclass
import logging
from pathlib import Path
import re
from typing import (
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
)

from elasticsearch.helpers import async_bulk

from bot.services.reindex.series_scanner import SeriesScanner
from bot.services.reindex.video_path_transformer import VideoPathTransformer
from bot.services.reindex.zip_extractor import ZipExtractor
from bot.settings import settings
from preprocessor.search.elastic_manager import ElasticSearchManager


@dataclass
class ReindexResult:
    series_name: str
    episodes_processed: int
    documents_indexed: int
    errors: List[str]

    @property
    def summary(self) -> str:
        error_str = f", {len(self.errors)} errors" if self.errors else ""
        return (
            f"Series: {self.series_name}, "
            f"Episodes: {self.episodes_processed}, "
            f"Documents: {self.documents_indexed}"
            f"{error_str}"
        )


class ReindexService:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.scanner = SeriesScanner(logger)
        self.zip_extractor = ZipExtractor(logger)
        self.video_transformer = VideoPathTransformer(logger)
        self.es_manager: Optional[ElasticSearchManager] = None

    async def _init_elasticsearch(self):
        if self.es_manager is None:
            self.es_manager = await ElasticSearchManager.connect_to_elasticsearch(
                settings.ES_HOST,
                settings.ES_USER,
                settings.ES_PASS.get_secret_value(),
                self.logger,
            )

    async def reindex_all(
        self,
        progress_callback: Callable[[str, int, int], Awaitable[None]],
    ) -> List[ReindexResult]:
        await self._init_elasticsearch()

        all_series = self.scanner.scan_all_series()
        results = []

        total_series = len(all_series)
        for idx, series_name in enumerate(all_series):
            await progress_callback(
                f"Processing series {idx+1}/{total_series}: {series_name}",
                idx,
                total_series,
            )

            result = await self.reindex_series(series_name, progress_callback)
            results.append(result)

        return results

    async def reindex_all_new(
        self,
        progress_callback: Callable[[str, int, int], Awaitable[None]],
    ) -> List[ReindexResult]:
        await self._init_elasticsearch()

        all_series = self.scanner.scan_all_series()
        new_series = []

        for series_name in all_series:
            index_exists = await self.es_manager.indices.exists(
                index=f"{series_name}_segments",
            )
            if not index_exists:
                new_series.append(series_name)

        if not new_series:
            await progress_callback("No new series to reindex", 0, 0)
            return []

        results = []
        total_series = len(new_series)

        for idx, series_name in enumerate(new_series):
            await progress_callback(
                f"Processing new series {idx+1}/{total_series}: {series_name}",
                idx,
                total_series,
            )

            result = await self.reindex_series(series_name, progress_callback)
            results.append(result)

        return results

    async def reindex_series( # pylint: disable=too-many-locals
        self,
        series_name: str,
        progress_callback: Callable[[str, int, int], Awaitable[None]],
    ) -> ReindexResult:
        await self._init_elasticsearch()

        await progress_callback(f"Scanning {series_name}...", 0, 100)

        zip_files = self.scanner.scan_series_zips(series_name)
        if not zip_files:
            raise ValueError(f"No zip files found for series: {series_name}")

        mp4_map = self.scanner.scan_series_mp4s(series_name)

        await progress_callback(f"Deleting old indices for {series_name}...", 5, 100)
        await self._delete_series_indices(series_name)

        total_episodes = len(zip_files)
        indexed_count = 0
        errors = []

        for idx, zip_path in enumerate(zip_files):
            try:
                episode_code = self._extract_episode_code(zip_path)
                progress_pct = 10 + int((idx / total_episodes) * 85)

                await progress_callback(
                    f"Processing {episode_code}... ({idx+1}/{total_episodes})",
                    progress_pct,
                    100,
                )

                mp4_path = mp4_map.get(episode_code)

                jsonl_contents = self.zip_extractor.extract_to_memory(zip_path)

                for jsonl_type, buffer in jsonl_contents.items():
                    documents = self.zip_extractor.parse_jsonl_from_memory(buffer)

                    for doc in documents:
                        self.video_transformer.transform_video_path(doc, mp4_path)

                    index_name = self._get_index_name(series_name, jsonl_type)

                    await self._bulk_index_documents(
                        index_name,
                        jsonl_type,
                        documents,
                    )

                    indexed_count += len(documents)

            except Exception as e:
                error_msg = f"Failed to process {zip_path.name}: {str(e)}"
                self.logger.error(error_msg, exc_info=True)
                errors.append(error_msg)

        await progress_callback(f"Reindex of {series_name} complete!", 100, 100)

        return ReindexResult(
            series_name=series_name,
            episodes_processed=total_episodes - len(errors),
            documents_indexed=indexed_count,
            errors=errors,
        )

    async def _delete_series_indices(self, series_name: str):
        index_types = [
            "segments",
            "text_embeddings",
            "video_frames",
            "episode_names",
            "full_episode_embeddings",
            "sound_events",
            "sound_event_embeddings",
        ]

        for index_type in index_types:
            index_name = f"{series_name}_{index_type}"
            try:
                if await self.es_manager.indices.exists(index=index_name):
                    await self.es_manager.indices.delete(index=index_name)
                    self.logger.info(f"Deleted index: {index_name}")
            except Exception as e:
                self.logger.warning(f"Failed to delete index {index_name}: {e}")

    async def _bulk_index_documents(
        self,
        index_name: str,
        index_type: str,
        documents: List[Dict],
    ):
        mapping = self._get_mapping_for_type(index_type)

        if not await self.es_manager.indices.exists(index=index_name):
            await self.es_manager.indices.create(
                index=index_name,
                body=mapping,
            )

        actions = [
            {
                "_index": index_name,
                "_source": doc,
            }
            for doc in documents
        ]

        await async_bulk(
            self.es_manager,
            actions,
            chunk_size=50,
            max_chunk_bytes=5 * 1024 * 1024,
        )

        self.logger.info(f"Indexed {len(documents)} documents to {index_name}")

    def _get_mapping_for_type(self, index_type: str):
        mappings = {
            "text_segments": ElasticSearchManager.SEGMENTS_INDEX_MAPPING,
            "text_embeddings": ElasticSearchManager.TEXT_EMBEDDINGS_INDEX_MAPPING,
            "video_frames": ElasticSearchManager.VIDEO_EMBEDDINGS_INDEX_MAPPING,
            "episode_names": ElasticSearchManager.EPISODE_NAMES_INDEX_MAPPING,
            "full_episode_embeddings": ElasticSearchManager.FULL_EPISODE_EMBEDDINGS_INDEX_MAPPING,
            "sound_events": ElasticSearchManager.SOUND_EVENTS_INDEX_MAPPING,
            "sound_event_embeddings": ElasticSearchManager.SOUND_EVENT_EMBEDDINGS_INDEX_MAPPING,
        }
        return mappings.get(index_type, ElasticSearchManager.SEGMENTS_INDEX_MAPPING)

    def _get_index_name(self, series_name: str, jsonl_type: str) -> str:
        return f"{series_name}_{jsonl_type}"

    def _extract_episode_code(self, zip_path: Path) -> str:
        match = re.search(r'(S\d{2}E\d{2})', zip_path.name)
        if match:
            return match.group(1)
        return zip_path.stem
