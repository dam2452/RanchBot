import asyncio
import json
import logging
from pathlib import Path
from typing import (
    Awaitable,
    Callable,
    List,
    Optional,
)

from elasticsearch import exceptions as es_exceptions
from elasticsearch.helpers import (
    BulkIndexError,
    async_bulk,
)
from rich.console import Console

from bot.search.elastic_search_manager import ElasticSearchManager
from preprocessor.state_manager import StateManager
from preprocessor.utils.error_handling_logger import ErrorHandlingLogger

console = Console()


class ElasticSearchIndexer:
    def __init__(self, args: dict):
        self.__dry_run = args.get("dry_run", False)
        self.__name = args["name"]
        self.__transcription_jsons = args["transcription_jsons"]
        self.__append = args.get("append", False)

        self.__logger: ErrorHandlingLogger = ErrorHandlingLogger(
            class_name=self.__class__.__name__,
            loglevel=logging.DEBUG,
            error_exit_code=1,
        )

        self.state_manager: Optional[StateManager] = args.get("state_manager")
        self.series_name: str = args.get("series_name", "unknown")

    def __call__(self) -> None:
        asyncio.run(self.__exec())

    def work(self) -> int:
        try:
            asyncio.run(self.__exec())
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.__logger.error(f"Unexpected error during Elasticsearch indexing: {e}")
        return self.__logger.finalize()

    async def __exec(self) -> None:
        self.__client = await ElasticSearchManager.connect_to_elasticsearch(self.__logger)

        try:
            if not self.__append:
                await self.__delete_index()
                await self.__create_index()
            elif not await self.__client.indices.exists(index=self.__name):
                self.__logger.info(
                    f"Index '{self.__name}' does not exist. Creating it since --append was used.",
                )
                await self.__create_index()
            else:
                self.__logger.info(f"Append mode: not deleting nor recreating index '{self.__name}'.")

            await self.__index_transcriptions()

            if not self.__dry_run:
                await self.__print_one_transcription()
        finally:
            await self.__client.close()

    async def __create_index(self) -> None:
        async def operation():
            if await self.__client.indices.exists(index=self.__name):
                self.__logger.info(f"Index '{self.__name}' already exists.")
            else:
                await self.__client.indices.create(
                    index=self.__name,
                    body=ElasticSearchManager.INDEX_MAPPING,
                )
                self.__logger.info(f"Index '{self.__name}' created.")

        await self.__do_crud(operation)

    async def __delete_index(self) -> None:
        async def operation():
            if await self.__client.indices.exists(index=self.__name):
                await self.__client.indices.delete(index=self.__name)
                self.__logger.info(f"Deleted index: {self.__name}")
            else:
                self.__logger.info(f"Index '{self.__name}' does not exist. No action taken.")

        await self.__do_crud(operation)

    async def __do_crud(self, operation: Callable[[], Awaitable[None]]) -> None:
        try:
            await operation()
        except es_exceptions.RequestError as e:
            self.__logger.error(f"Failed operation on index '{self.__name}': {e}")
            raise
        except es_exceptions.ConnectionError as e:
            self.__logger.error(f"Connection error: {e}")
            raise

    async def __index_transcriptions(self) -> None:
        actions = await self.__load_all_seasons_actions()

        if not actions:
            self.__logger.info("No data to index.")
            return

        self.__logger.info(
            f"Prepared {len(actions)} segments for indexing into '{self.__name}'.",
        )

        if self.__dry_run:
            for action in actions:
                self.__logger.info(
                    f"Prepared action: {json.dumps(action, indent=2)}",
                )
            self.__logger.info("Dry-run complete. No data sent to Elasticsearch.")
        else:
            try:
                await async_bulk(self.__client, actions)
                self.__logger.info("Data indexed successfully.")
            except BulkIndexError as e:
                self.__logger.error(f"Bulk indexing failed: {len(e.errors)} errors.")
                for error in e.errors:
                    self.__logger.error(f"Failed document: {json.dumps(error, indent=2)}")

    async def __load_all_seasons_actions(self) -> List[dict]:
        actions = []

        for entry in self.__transcription_jsons.iterdir():
            if entry.is_dir():
                season_actions = await self.__load_season(entry)
                actions += season_actions
            elif entry.is_file() and entry.suffix == ".json":
                self.__logger.error(
                    f"JSON file {entry} found directly in {self.__transcription_jsons}, expected in season directory.",
                )
        return actions

    async def __load_season(self, season_path: Path) -> List[dict]:
        season_actions = []

        for episode_file in season_path.iterdir():
            if episode_file.suffix == ".json":
                self.__logger.info(f"Processing file: {episode_file}")
                season_actions += await self.__load_episode(episode_file)

        return season_actions

    async def __load_episode(self, episode_file: Path) -> List[dict]:
        with episode_file.open("r", encoding="utf-8") as f:
            data = json.load(f)

        episode_info = data.get("episode_info", {})
        season = episode_info.get("season")
        episode = episode_info.get("episode_number")

        if season is None or episode is None:
            self.__logger.error(f"Episode info missing in {episode_file}")
            return []

        if "is_special_feature" not in episode_info:
            episode_info["is_special_feature"] = season == 0

        if season == 0 and "special_feature_type" not in episode_info:
            episode_info["special_feature_type"] = "special"

        series_name = self.__name.lower()
        new_name = f"{series_name}_S{season:02d}E{episode:02d}.mp4"
        if season == 0:
            video_path = Path("bot") / f"{series_name.upper()}-WIDEO" / "Specjalne" / new_name
        else:
            video_path = Path("bot") / f"{series_name.upper()}-WIDEO" / f"Sezon {season}" / new_name

        transcription = data.get("transcription", {})
        scene_timestamps = data.get("scene_timestamps", {})
        text_embeddings = data.get("text_embeddings", [])
        video_embeddings = data.get("video_embeddings", [])

        actions = []
        for segment in data.get("segments", []):
            if not all(key in segment for key in ("text", "start", "end")):
                self.__logger.error(f"Skipping invalid segment in {episode_file}")
                continue

            source = {
                "episode_info": episode_info,
                "text": segment.get("text"),
                "start": segment.get("start"),
                "end": segment.get("end"),
                "id": segment.get("id"),
                "seek": segment.get("seek"),
                "author": segment.get("author", ""),
                "comment": segment.get("comment", ""),
                "tags": segment.get("tags", []),
                "location": segment.get("location", ""),
                "actors": segment.get("actors", []),
                "video_path": video_path.as_posix(),
            }

            if transcription:
                source["transcription"] = transcription

            if scene_timestamps:
                source["scene_timestamps"] = scene_timestamps

            if text_embeddings:
                source["text_embeddings"] = text_embeddings

            if video_embeddings:
                source["video_embeddings"] = video_embeddings

            actions.append({
                "_index": self.__name,
                "_source": source,
            })

        return actions

    async def __print_one_transcription(self) -> None:
        response = await self.__client.search(index=self.__name, size=1)
        if not response["hits"]["hits"]:
            self.__logger.error("No documents found.")
            return

        document = response["hits"]["hits"][0]["_source"]
        document["video_path"] = document["video_path"].replace("\\", "/")
        readable_output = (
            f"Document ID: {response['hits']['hits'][0]['_id']}\n"
            f"Episode Info: {document['episode_info']}\n"
            f"Video Path: {document['video_path']}\n"
            f"Segment Text: {document.get('text', 'No text available')}\n"
            f"Timestamp: {document.get('timestamp', 'No timestamp available')}"
        )
        self.__logger.info("Retrieved document:\n" + readable_output)
