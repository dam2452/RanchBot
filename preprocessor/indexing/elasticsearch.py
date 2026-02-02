import asyncio
import json
import logging
from pathlib import Path
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
)

from elasticsearch import exceptions as es_exceptions
from elasticsearch.helpers import (
    BulkIndexError,
    async_bulk,
)

from preprocessor.config.config import settings
from preprocessor.core.base_processor import BaseProcessor
from preprocessor.core.episode_manager import EpisodeManager
from preprocessor.search.elastic_manager import ElasticSearchManager
from preprocessor.utils.console import console

ELASTIC_SUBDIRS = settings.output_subdirs.elastic_document_subdirs


class ElasticSearchIndexer(BaseProcessor):
    def __init__(self, args: Dict[str, Any]) -> None:
        super().__init__(
            args=args,
            class_name=self.__class__.__name__,
            error_exit_code=1,
            loglevel=logging.DEBUG,
        )

        self.dry_run = self._args.get("dry_run", False)
        self.name = self._args["name"]
        self.elastic_documents_dir = self._args.get("elastic_documents_dir", Path("/app/output_data/elastic_documents"))
        self.transcription_jsons = self._args.get("transcription_jsons")
        self.append = self._args.get("append", False)

        episodes_info_json = self._args.get("episodes_info_json")
        self.episode_manager = EpisodeManager(episodes_info_json, self.series_name)
        self.client = None

    def _validate_args(self, args: Dict[str, Any]) -> None:
        if "name" not in args:
            raise ValueError("index name is required")

    @staticmethod
    def __sanitize_error_for_logging(error: Dict[str, Any]) -> Dict[str, Any]:
        vector_keys = {"text_embedding", "video_embedding", "title_embedding", "embedding"}

        def truncate_vectors(obj):
            if isinstance(obj, dict):
                return {
                    k: f"[vector dim={len(v)}]" if k in vector_keys and isinstance(v, list) else truncate_vectors(v)
                    for k, v in obj.items()
                }
            if isinstance(obj, list) and len(obj) > 10:
                return obj[:3] + ["..."]
            return obj

        return truncate_vectors(error)

    def __call__(self) -> None:
        asyncio.run(self.__exec_async())

    def _execute(self) -> None:
        asyncio.run(self.__exec_async())

    def __check_files_exist(self) -> bool:
        if not self.elastic_documents_dir.exists():
            return False

        return any([
            any(self.elastic_documents_dir.glob(f"{ELASTIC_SUBDIRS.text_segments}/**/*.jsonl")),
            any(self.elastic_documents_dir.glob(f"{ELASTIC_SUBDIRS.text_embeddings}/**/*.jsonl")),
            any(self.elastic_documents_dir.glob(f"{ELASTIC_SUBDIRS.video_frames}/**/*.jsonl")),
            any(self.elastic_documents_dir.glob(f"{ELASTIC_SUBDIRS.episode_names}/**/*.jsonl")),
            any(self.elastic_documents_dir.glob(f"{ELASTIC_SUBDIRS.full_episode_embeddings}/**/*.jsonl")),
            any(self.elastic_documents_dir.glob(f"{ELASTIC_SUBDIRS.sound_events}/**/*.jsonl")),
            any(self.elastic_documents_dir.glob(f"{ELASTIC_SUBDIRS.sound_event_embeddings}/**/*.jsonl")),
        ])

    async def __exec_async(self) -> None:
        if not self.__check_files_exist():
            self.logger.info("No elastic documents found to index.")
            return

        try:
            self.client = await ElasticSearchManager.connect_to_elasticsearch(
                settings.elasticsearch.host,
                settings.elasticsearch.user,
                settings.elasticsearch.password,
                self.logger,
            )
        except es_exceptions.ConnectionError:
            console.print("[red]✗ Failed to connect to Elasticsearch[/red]")
            console.print(f"[yellow]Make sure Elasticsearch is running at: {settings.elasticsearch.host}[/yellow]")
            console.print("[yellow]Run: docker-compose -f docker-compose.test.yml up -d[/yellow]")
            return

        try:
            indices = {
                ELASTIC_SUBDIRS.text_segments: f"{self.name}_segments",
                ELASTIC_SUBDIRS.text_embeddings: f"{self.name}_text_embeddings",
                ELASTIC_SUBDIRS.video_frames: f"{self.name}_video_frames",
                ELASTIC_SUBDIRS.episode_names: f"{self.name}_episode_names",
                ELASTIC_SUBDIRS.full_episode_embeddings: f"{self.name}_full_episode_embeddings",
                ELASTIC_SUBDIRS.sound_events: f"{self.name}_sound_events",
                ELASTIC_SUBDIRS.sound_event_embeddings: f"{self.name}_sound_event_embeddings",
            }

            for doc_type, index_name in indices.items():
                console.print(f"[cyan]Processing {doc_type} → {index_name}[/cyan]")

                if not self.append:
                    await self.__delete_index(index_name)
                    await self.__create_index(index_name, doc_type)
                elif not await self.client.indices.exists(index=index_name):
                    self.logger.info(f"Index '{index_name}' does not exist. Creating it.")
                    await self.__create_index(index_name, doc_type)
                else:
                    self.logger.info(f"Append mode: not deleting nor recreating index '{index_name}'.")

                await self.__index_documents(doc_type, index_name)

            if not self.dry_run:
                for doc_type, index_name in indices.items():
                    if await self.client.indices.exists(index=index_name):
                        await self.__print_sample_document(index_name)
        finally:
            await self.client.close()

    async def __create_index(self, index_name: str, doc_type: str) -> None:
        mappings = {
            ELASTIC_SUBDIRS.text_segments: ElasticSearchManager.SEGMENTS_INDEX_MAPPING,
            ELASTIC_SUBDIRS.text_embeddings: ElasticSearchManager.TEXT_EMBEDDINGS_INDEX_MAPPING,
            ELASTIC_SUBDIRS.video_frames: ElasticSearchManager.VIDEO_EMBEDDINGS_INDEX_MAPPING,
            ELASTIC_SUBDIRS.episode_names: ElasticSearchManager.EPISODE_NAMES_INDEX_MAPPING,
            ELASTIC_SUBDIRS.full_episode_embeddings: ElasticSearchManager.FULL_EPISODE_EMBEDDINGS_INDEX_MAPPING,
            ELASTIC_SUBDIRS.sound_events: ElasticSearchManager.SOUND_EVENTS_INDEX_MAPPING,
            ELASTIC_SUBDIRS.sound_event_embeddings: ElasticSearchManager.SOUND_EVENT_EMBEDDINGS_INDEX_MAPPING,
        }

        async def operation():
            if await self.client.indices.exists(index=index_name):
                self.logger.info(f"Index '{index_name}' already exists.")
            else:
                await self.client.indices.create(
                    index=index_name,
                    body=mappings[doc_type],
                )
                self.logger.info(f"Index '{index_name}' created.")

        await self.__do_crud(operation, index_name)

    async def __delete_index(self, index_name: str) -> None:
        async def operation():
            if await self.client.indices.exists(index=index_name):
                await self.client.indices.delete(index=index_name)
                self.logger.info(f"Deleted index: {index_name}")
            else:
                self.logger.info(f"Index '{index_name}' does not exist. No action taken.")

        await self.__do_crud(operation, index_name)

    async def __do_crud(self, operation: Callable[[], Awaitable[None]], index_name: str) -> None:
        try:
            await operation()
        except es_exceptions.RequestError as e:
            self.logger.error(f"Failed operation on index '{index_name}': {e}")
            raise
        except es_exceptions.ConnectionError as e:
            self.logger.error(f"Connection error: {e}")
            raise

    async def __index_documents(self, doc_type: str, index_name: str) -> None:
        jsonl_files = list(self.elastic_documents_dir.glob(f"{doc_type}/**/*.jsonl"))

        if not jsonl_files:
            self.logger.info(f"No {doc_type} documents found. Skipping.")
            return

        actions = self.__load_jsonl_files(jsonl_files, index_name)

        if not actions:
            self.logger.info(f"No {doc_type} documents to index.")
            return

        console.print(f"[cyan]Prepared {len(actions)} {doc_type} documents for indexing[/cyan]")

        if self.dry_run:
            self.logger.info(f"Dry-run: would index {len(actions)} documents to '{index_name}'")
            if actions:
                sample = json.dumps(actions[0], indent=2, ensure_ascii=False)[:500]
                self.logger.info(f"Sample document:\n{sample}...")
        else:
            try:
                await async_bulk(
                    self.client,
                    actions,
                    chunk_size=50,
                    max_chunk_bytes=5 * 1024 * 1024,
                )
                console.print(f"[green]✓ Indexed {len(actions)} {doc_type} documents → {index_name}[/green]")
            except BulkIndexError as e:
                self.logger.error(f"Bulk indexing failed: {len(e.errors)} errors.")
                for error in e.errors[:3]:
                    sanitized = self.__sanitize_error_for_logging(error)
                    self.logger.error(f"Failed document: {json.dumps(sanitized, indent=2)}")
                if len(e.errors) > 10:
                    self.logger.error(f"... and {len(e.errors) - 10} more errors")

    def __load_jsonl_files(self, jsonl_files: List[Path], index_name: str) -> List[Dict[str, Any]]:
        actions = []

        for jsonl_file in jsonl_files:
            self.logger.info(f"Loading {jsonl_file.name}")
            with open(jsonl_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        doc = json.loads(line)
                        actions.append({
                            "_index": index_name,
                            "_source": doc,
                        })

        return actions

    def _load_jsonl_documents(self, doc_dir: Path, index_name: str) -> List[Dict[str, Any]]:
        actions = []

        for jsonl_file in doc_dir.rglob("*.jsonl"):
            self.logger.info(f"Loading {jsonl_file.name}")
            with open(jsonl_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        doc = json.loads(line)
                        actions.append({
                            "_index": index_name,
                            "_source": doc,
                        })

        return actions

    async def __print_sample_document(self, index_name: str) -> None:
        try:  # pylint: disable=too-many-try-statements
            response = await self.client.search(index=index_name, size=1)
            if not response["hits"]["hits"]:
                self.logger.info(f"No documents found in {index_name}.")
                return

            document = response["hits"]["hits"][0]["_source"]
            doc_id = response["hits"]["hits"][0]["_id"]

            console.print(f"\n[cyan]Sample document from {index_name}:[/cyan]")
            console.print(f"  Document ID: {doc_id}")

            if "episode_id" in document:
                console.print(f"  Episode: {document['episode_id']}")
            if "video_path" in document:
                console.print(f"  Video: {document['video_path']}")
            if "text" in document:
                text_preview = document['text'][:100]
                console.print(f"  Text: {text_preview}...")
            if "perceptual_hash" in document:
                console.print(f"  Hash: {document['perceptual_hash']}")
            if "timestamp" in document:
                console.print(f"  Timestamp: {document['timestamp']}")

        except Exception as e:
            self.logger.error(f"Failed to retrieve sample document: {e}")
