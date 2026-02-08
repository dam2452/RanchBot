import asyncio
from dataclasses import dataclass
import logging
from pathlib import Path
import re
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
)

from elasticsearch.helpers import (
    BulkIndexError,
    async_bulk,
)

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
    def __init__(self, logger: logging.Logger) -> None:
        self.__logger = logger
        self.__scanner = SeriesScanner(logger)
        self.__zip_extractor = ZipExtractor(logger)
        self.__video_transformer = VideoPathTransformer(logger)
        self.__es_manager: Optional[ElasticSearchManager] = None

    async def __aenter__(self) -> "ReindexService":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.__close()

    async def __close(self) -> None:
        if self.__es_manager is not None:
            try:
                await self.__es_manager.close()
            except Exception as e:
                self.__logger.warning(f"Error closing ES connection: {e}")
            finally:
                self.__es_manager = None

    async def reindex_all(
        self,
        progress_callback: Callable[[str, int, int], Awaitable[None]],
    ) -> List[ReindexResult]:
        await self.__init_elasticsearch()

        all_series = self.__scanner.scan_all_series()
        results = []

        total_series = len(all_series)
        for idx, series_name in enumerate(all_series):
            await progress_callback(
                f"Przetwarzanie serialu {idx+1}/{total_series}: {series_name}",
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
        await self.__init_elasticsearch()

        all_series = self.__scanner.scan_all_series()
        new_series = []

        for series_name in all_series:
            index_exists = await self.__es_manager.indices.exists(
                index=f"{series_name}_text_segments",
            )
            if not index_exists:
                new_series.append(series_name)

        if not new_series:
            await progress_callback("Brak nowych seriali do reindeksowania", 0, 0)
            return []

        results = []
        total_series = len(new_series)

        for idx, series_name in enumerate(new_series):
            await progress_callback(
                f"Przetwarzanie nowego serialu {idx+1}/{total_series}: {series_name}",
                idx,
                total_series,
            )

            result = await self.reindex_series(series_name, progress_callback)
            results.append(result)

        return results

    async def reindex_series(
        self,
        series_name: str,
        progress_callback: Callable[[str, int, int], Awaitable[None]],
    ) -> ReindexResult:
        await self.__init_elasticsearch()

        await progress_callback(f"Skanowanie {series_name}...", 0, 100)

        zip_files = self.__scanner.scan_series_zips(series_name)
        if not zip_files:
            raise ValueError(f"No zip files found for series: {series_name}")

        mp4_map = self.__scanner.scan_series_mp4s(series_name)

        await progress_callback(f"Usuwanie starych indeksów dla {series_name}...", 5, 100)
        await self.__delete_series_indices(series_name)

        total_episodes = len(zip_files)
        indexed_count = 0
        errors = []

        for idx, zip_path in enumerate(zip_files):
            try:
                if idx > 0 and idx % 10 == 0:
                    await self.__refresh_elasticsearch_connection(series_name, idx)

                _, indexed_in_episode = await self.__process_single_episode(
                    zip_path,
                    series_name,
                    mp4_map,
                    idx,
                    total_episodes,
                    progress_callback,
                )

                indexed_count += indexed_in_episode

            except Exception as e:
                error_msg = f"Failed to process {zip_path.name}: {str(e)}"
                self.__logger.error(error_msg, exc_info=True)
                errors.append(error_msg)

                if "Cannot connect" in str(e) or "Connection" in str(e):
                    self.__logger.info("Connection error detected, recreating ES connection...")
                    try:
                        if self.__es_manager:
                            await self.__es_manager.close()
                    except Exception:
                        pass
                    self.__es_manager = None
                    await self.__init_elasticsearch()

        await progress_callback(f"Reindeksowanie {series_name} zakończone!", 100, 100)

        return ReindexResult(
            series_name=series_name,
            episodes_processed=total_episodes - len(errors),
            documents_indexed=indexed_count,
            errors=errors,
        )

    async def __init_elasticsearch(self) -> None:
        if self.__es_manager is None:
            self.__es_manager = await ElasticSearchManager.connect_to_elasticsearch(
                settings.ES_HOST,
                settings.ES_USER,
                settings.ES_PASS.get_secret_value(),
                self.__logger,
            )

    async def __delete_series_indices(self, series_name: str) -> None:
        index_types = [
            "text_segments",
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
                if await self.__es_manager.indices.exists(index=index_name):
                    await self.__es_manager.indices.delete(index=index_name)
                    self.__logger.info(f"Deleted index: {index_name}")
            except Exception as e:
                self.__logger.warning(f"Failed to delete index {index_name}: {e}")

    async def __bulk_index_documents(
        self,
        index_name: str,
        index_type: str,
        documents: List[Dict[str, Any]],
    ) -> None:
        mapping = self.__get_mapping_for_type(index_type)

        if not await self.__es_manager.indices.exists(index=index_name):
            await self.__es_manager.indices.create(
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

        try:
            await async_bulk(
                self.__es_manager,
                actions,
                chunk_size=5,
                max_chunk_bytes=512 * 1024,
                raise_on_error=False,
                max_retries=2,
                initial_backoff=1,
                max_backoff=300,
            )
            self.__logger.info(f"Indexed {len(documents)} documents to {index_name}")
            await asyncio.sleep(2.0)
        except BulkIndexError as e:
            self.__logger.warning(f"Bulk index errors in {index_name}: {len(e.errors)} failed")
            for error in e.errors[:3]:
                self.__logger.warning(f"Sample error: {error}")
            raise

    async def __refresh_elasticsearch_connection(self, series_name: str, idx: int) -> None:
        self.__logger.info(f"Flushing and refreshing ES after {idx} episodes...")
        try:
            if self.__es_manager:
                await self.__es_manager.indices.flush(
                    index=f"{series_name}_*",
                    wait_if_ongoing=False,
                    ignore=[404],
                )
                await asyncio.sleep(3)
                await self.__es_manager.close()
        except Exception as e:
            self.__logger.warning(f"Error during flush: {e}")
        self.__es_manager = None
        await asyncio.sleep(5)
        await self.__init_elasticsearch()
        await asyncio.sleep(2)

    async def __process_single_episode(
        self,
        zip_path: Path,
        series_name: str,
        mp4_map: Dict[str, str],
        idx: int,
        total_episodes: int,
        progress_callback: Callable[[str, int, int], Awaitable[None]],
    ) -> Tuple[str, int]:
        episode_code = self.__extract_episode_code(zip_path)
        progress_pct = 10 + int((idx / total_episodes) * 85)

        await progress_callback(
            f"Przetwarzanie {episode_code}... ({idx+1}/{total_episodes})",
            progress_pct,
            100,
        )

        mp4_path = mp4_map.get(episode_code)
        jsonl_contents = self.__zip_extractor.extract_to_memory(zip_path)
        indexed_count = 0

        for jsonl_type, buffer in jsonl_contents.items():
            documents = self.__zip_extractor.parse_jsonl_from_memory(buffer)

            for doc in documents:
                self.__video_transformer.transform_video_path(doc, mp4_path)

            index_name = self.__get_index_name(series_name, jsonl_type)

            await self.__bulk_index_documents(
                index_name,
                jsonl_type,
                documents,
            )

            indexed_count += len(documents)

        return episode_code, indexed_count

    @staticmethod
    def __get_mapping_for_type(index_type: str) -> Dict[str, Any]:
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

    @staticmethod
    def __get_index_name(series_name: str, jsonl_type: str) -> str:
        return f"{series_name}_{jsonl_type}"

    @staticmethod
    def __extract_episode_code(zip_path: Path) -> str:
        match = re.search(r'(S\d{2}E\d{2})', zip_path.name)
        if match:
            return match.group(1)
        return zip_path.stem
