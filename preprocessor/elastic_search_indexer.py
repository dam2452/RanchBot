import asyncio
import json
import logging
from pathlib import Path
from typing import (
    Awaitable,
    Callable,
    List,
)

from elasticsearch import exceptions as es_exceptions
from elasticsearch.helpers import (
    BulkIndexError,
    async_bulk,
)

from bot.database.database_manager import DatabaseManager
from bot.search.elastic_search_manager import ElasticSearchManager
from preprocessor.utils.error_handling_logger import ErrorHandlingLogger


class ElasticSearchIndexer:
    def __init__(self, args: json):
        self.__dry_run: bool = args["dry_run"]
        self.__name: str = args["name"]

        self.__transcoded_videos: Path = args["transcoded_videos"]
        self.__transcription_jsons: Path = args["transcription_jsons"]

        self.__logger: ErrorHandlingLogger = ErrorHandlingLogger(
            class_name=self.__class__.__name__,
            loglevel=logging.DEBUG,
            error_exit_code=1,
        )

    def __call__(self) -> None:
        asyncio.run(self.__exec())

    async def __exec(self) -> None:
        await DatabaseManager.init_pool()

        self.__client = await ElasticSearchManager.connect_to_elasticsearch(self.__logger)

        try:
            await self.__delete_index()
            await self.__create_index()
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
                await self.__client.indices.create(index=self.__name, body=ElasticSearchManager.INDEX_MAPPING)
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

        self.__logger.info(f"Prepared {len(actions)} segments for indexing into '{self.__name}'.")

        if self.__dry_run:
            for action in actions:
                self.__logger.info(f"Prepared action: {json.dumps(action, indent=2)}")
            self.__logger.info("Dry-run complete. No data sent to Elasticsearch.")
        else:
            try:
                await async_bulk(self.__client, actions)
                self.__logger.info("Data indexed successfully.")
            except BulkIndexError as e:
                self.__logger.error(f"Bulk indexing failed: {len(e.errors)} errors.")
                for error in e.errors:
                    self.__logger.error(f"Failed document: {json.dumps(error, indent=2)}")


    async def __load_all_seasons_actions(self) -> List[json]:
        actions = []

        for season_path in self.__transcription_jsons.iterdir():
            if season_path.is_dir():
                season_actions = await self.__load_season(season_path)
                actions += season_actions

        return actions

    async def __load_season(self, season_path: Path) -> List[json]:
        season_actions = []
        season_dir = season_path.name

        for episode_file in season_path.iterdir():
            if episode_file.suffix == ".json":
                self.__logger.info(f"Processing file: {episode_file}")
                season_actions += await self.__load_episode(episode_file, season_dir)

        return season_actions

    async def __load_episode(self, episode_file: Path, season_dir: str) -> List[json]:
        with episode_file.open("r", encoding="utf-8") as f:
            data = json.load(f).get("episode_info", {})

        episode_info = data.get("episode_info", {})
        video_path = self.__transcoded_videos / season_dir / (episode_file.stem + ".mp4")

        actions = []
        for segment in data.get("segments", []):
            if not all(key in segment for key in ("text", "start", "end")):
                self.__logger.error(f"Skipping invalid segment in {episode_file}")
                continue

            actions.append(
                {
                    "_index": self.__name,
                    "_source": {
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
                    },
                },
            )

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
