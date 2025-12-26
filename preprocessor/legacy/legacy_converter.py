import asyncio
import json
import logging
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from elasticsearch.helpers import (
    async_bulk,
    async_scan,
)

from preprocessor.config.config import settings
from preprocessor.core.base_processor import BaseProcessor
from preprocessor.search.elastic_manager import ElasticSearchManager
from preprocessor.utils.console import (
    console,
    create_progress,
)


class LegacyConverter(BaseProcessor):
    def _validate_args(self, args: Dict[str, Any]) -> None:
        if "index_name" not in args:
            raise ValueError("index_name is required")

    def __init__(self, args: Dict[str, Any]):
        super().__init__(
            args=args,
            class_name=self.__class__.__name__,
            error_exit_code=6,
            loglevel=logging.DEBUG,
        )

        self.index_name: str = self._args["index_name"]
        self.backup_file: Optional[Path] = self._args.get("backup_file")
        self.dry_run: bool = self._args.get("dry_run", False)

        self.client = None

    def _execute(self) -> None:
        asyncio.run(self.__exec())

    async def __exec(self) -> None:
        self.client = await ElasticSearchManager.connect_to_elasticsearch(  # pylint: disable=duplicate-code
            settings.elasticsearch.host,
            settings.elasticsearch.user,
            settings.elasticsearch.password,
            self.logger,
        )

        try:  # pylint: disable=too-many-try-statements
            if not await self.client.indices.exists(index=self.index_name):
                self.logger.error(f"Index '{self.index_name}' does not exist")
                return

            console.print(f"[blue]Converting documents in index: {self.index_name}[/blue]")

            if self.backup_file:
                await self.__backup_index()

            documents = await self.__fetch_all_documents()

            if not documents:
                console.print("[yellow]No documents found to convert[/yellow]")
                return

            console.print(f"[blue]Found {len(documents)} documents to convert[/blue]")

            converted = self.__convert_documents(documents)

            if self.dry_run:
                console.print("[yellow]Dry run - showing sample converted document:[/yellow]")
                console.print(json.dumps(converted[0], indent=2, ensure_ascii=False))
                console.print(f"[yellow]Would convert {len(converted)} documents[/yellow]")
            else:
                await self.__update_documents(converted)
                console.print(f"[green]Successfully converted {len(converted)} documents[/green]")

        finally:
            await self.client.close()

    async def __backup_index(self) -> None:
        console.print(f"[cyan]Creating backup: {self.backup_file}[/cyan]")

        documents = []
        async for doc in async_scan(
            self.client,
            index=self.index_name,
            query={"query": {"match_all": {}}},
        ):
            documents.append(doc)

        self.backup_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.backup_file, "w", encoding="utf-8") as f:
            json.dump(documents, f, indent=2, ensure_ascii=False)

        console.print(f"[green]Backup created: {len(documents)} documents[/green]")

    async def __fetch_all_documents(self) -> List[Dict]:
        console.print("[cyan]Fetching documents...[/cyan]")
        documents = []

        async for doc in async_scan(
            self.client,
            index=self.index_name,
            query={"query": {"match_all": {}}},
        ):
            documents.append(doc)

        console.print(f"[green]Fetched {len(documents)} documents[/green]")
        return documents

    def __convert_documents(self, documents: List[Dict]) -> List[Dict]:
        converted = []

        with create_progress() as progress:
            task = progress.add_task("Converting documents...", total=len(documents))

            for doc in documents:
                converted_doc = self.__convert_single_document(doc)
                converted.append(converted_doc)
                progress.advance(task)

        return converted

    def __convert_single_document(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        doc_id = doc["_id"]
        source = doc["_source"]

        converted_source: Dict[str, Any] = dict(source)

        if "transcription" not in converted_source:
            converted_source["transcription"] = {
                "format": "legacy_whisper",
                "segments": [{
                    "id": source.get("id"),
                    "start": source.get("start"),
                    "end": source.get("end"),
                    "text": source.get("text", ""),
                    "speaker": "unknown",
                }],
            }

        if "scene_timestamps" not in converted_source:
            converted_source["scene_timestamps"] = {}

        if "text_embeddings" not in converted_source:
            converted_source["text_embeddings"] = []

        if "video_embeddings" not in converted_source:
            converted_source["video_embeddings"] = []

        episode_info = converted_source.get("episode_info", {})
        if "description" not in episode_info:
            episode_info["description"] = ""
        if "summary" not in episode_info:
            episode_info["summary"] = ""
        converted_source["episode_info"] = episode_info

        return {
            "_id": doc_id,
            "_index": self.index_name,
            "_source": converted_source,
        }

    async def __update_documents(self, documents: List[Dict]) -> None:
        actions = []
        for doc in documents:
            actions.append({
                "_op_type": "update",
                "_index": doc["_index"],
                "_id": doc["_id"],
                "doc": doc["_source"],
            })

        with create_progress() as progress:
            task = progress.add_task("Updating documents...", total=len(actions))

            try:
                _, failed = await async_bulk(
                    self.client,
                    actions,
                    raise_on_error=False,
                )
                progress.update(task, completed=len(actions))  # pylint: disable=no-member

                if failed:
                    self.logger.error(f"Failed to update {len(failed)} documents")
                    for item in failed[:5]:
                        self.logger.error(f"Failed: {item}")

            except Exception as e:
                self.logger.error(f"Bulk update failed: {e}")
                raise
