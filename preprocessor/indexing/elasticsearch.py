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
        self.transcription_jsons = self._args["transcription_jsons"]
        self.append = self._args.get("append", False)

        episodes_info_json = self._args.get("episodes_info_json")
        self.episode_manager = EpisodeManager(episodes_info_json, self.series_name)
        self.client = None

    def _validate_args(self, args: Dict[str, Any]) -> None:
        if "name" not in args:
            raise ValueError("index name is required")
        if "transcription_jsons" not in args:
            raise ValueError("transcription_jsons path is required")

    def __call__(self) -> None:
        asyncio.run(self._exec_async())

    def _execute(self) -> None:
        asyncio.run(self._exec_async())

    def _check_files_exist(self) -> bool:
        if not Path(self.transcription_jsons).exists():
            return False

        has_files = False
        for entry in Path(self.transcription_jsons).iterdir():
            if entry.is_dir():
                if any(f.suffix == ".json" for f in entry.iterdir()):
                    has_files = True
                    break
            elif entry.is_file() and entry.suffix == ".json":
                has_files = True
                break

        return has_files

    async def _exec_async(self) -> None:
        if not self._check_files_exist():
            self.logger.info("No transcription files found to index.")
            return

        self.client = await ElasticSearchManager.connect_to_elasticsearch(  # pylint: disable=duplicate-code
            settings.elasticsearch.host,
            settings.elasticsearch.user,
            settings.elasticsearch.password,
            self.logger,
        )

        try:
            if not self.append:
                await self._delete_index()
                await self._create_index()
            elif not await self.client.indices.exists(index=self.name):
                self.logger.info(
                    f"Index '{self.name}' does not exist. Creating it since --append was used.",
                )
                await self._create_index()
            else:
                self.logger.info(f"Append mode: not deleting nor recreating index '{self.name}'.")

            await self._index_transcriptions()

            if not self.dry_run:
                await self._print_one_transcription()
        finally:
            await self.client.close()

    async def _create_index(self) -> None:
        async def operation():
            if await self.client.indices.exists(index=self.name):
                self.logger.info(f"Index '{self.name}' already exists.")
            else:
                await self.client.indices.create(
                    index=self.name,
                    body=ElasticSearchManager.INDEX_MAPPING,
                )
                self.logger.info(f"Index '{self.name}' created.")

        await self._do_crud(operation)

    async def _delete_index(self) -> None:
        async def operation():
            if await self.client.indices.exists(index=self.name):
                await self.client.indices.delete(index=self.name)
                self.logger.info(f"Deleted index: {self.name}")
            else:
                self.logger.info(f"Index '{self.name}' does not exist. No action taken.")

        await self._do_crud(operation)

    async def _do_crud(self, operation: Callable[[], Awaitable[None]]) -> None:
        try:
            await operation()
        except es_exceptions.RequestError as e:
            self.logger.error(f"Failed operation on index '{self.name}': {e}")
            raise
        except es_exceptions.ConnectionError as e:
            self.logger.error(f"Connection error: {e}")
            raise

    async def _index_transcriptions(self) -> None:
        actions = await self._load_all_seasons_actions()

        if not actions:
            self.logger.info("No data to index.")
            return

        self.logger.info(
            f"Prepared {len(actions)} segments for indexing into '{self.name}'.",
        )

        if self.dry_run:
            for action in actions:
                self.logger.info(
                    f"Prepared action: {json.dumps(action, indent=2)}",
                )
            self.logger.info("Dry-run complete. No data sent to Elasticsearch.")
        else:
            try:
                await async_bulk(self.client, actions)
                self.logger.info("Data indexed successfully.")
            except BulkIndexError as e:
                self.logger.error(f"Bulk indexing failed: {len(e.errors)} errors.")
                for error in e.errors:
                    self.logger.error(f"Failed document: {json.dumps(error, indent=2)}")

    async def _load_all_seasons_actions(self) -> List[Dict[str, Any]]:
        actions = []

        for entry in self.transcription_jsons.iterdir():
            if entry.is_dir():
                season_actions = await self._load_season(entry)
                actions += season_actions
            elif entry.is_file() and entry.suffix == ".json":
                self.logger.error(
                    f"JSON file {entry} found directly in {self.transcription_jsons}, expected in season directory.",
                )
        return actions

    async def _load_season(self, season_path: Path) -> List[Dict[str, Any]]:
        season_actions = []

        for episode_file in season_path.iterdir():
            if episode_file.suffix == ".json":
                self.logger.info(f"Processing file: {episode_file}")
                season_actions += await self._load_episode(episode_file)

        return season_actions

    async def _load_episode(self, episode_file: Path) -> List[Dict[str, Any]]:
        with episode_file.open("r", encoding="utf-8") as f:
            data = json.load(f)

        episode_info = data.get("episode_info", {})
        season = episode_info.get("season")
        episode = episode_info.get("episode_number")

        if season is None or episode is None:
            self.logger.error(f"Episode info missing in {episode_file}")
            return []

        if "is_special_feature" not in episode_info:
            episode_info["is_special_feature"] = season == 0

        if season == 0 and "special_feature_type" not in episode_info:
            episode_info["special_feature_type"] = "special"

        episode_obj = self.episode_manager.get_episode_by_season_and_relative(season, episode)
        if not episode_obj:
            self.logger.error(f"Cannot find episode info for S{season:02d}E{episode:02d}")
            return []

        video_path = self.episode_manager.build_video_path_for_elastic(episode_obj)

        transcription = data.get("transcription", {})
        scene_timestamps = data.get("scene_timestamps", {})
        text_embeddings = data.get("text_embeddings", [])
        video_embeddings = data.get("video_embeddings", [])

        actions = []
        for segment in data.get("segments", []):
            if not all(key in segment for key in ("text", "start", "end")):
                self.logger.error(f"Skipping invalid segment in {episode_file}")
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
                "video_path": video_path,
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
                "_index": self.name,
                "_source": source,
            })

        return actions

    async def _print_one_transcription(self) -> None:
        response = await self.client.search(index=self.name, size=1)
        if not response["hits"]["hits"]:
            self.logger.error("No documents found.")
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
        self.logger.info("Retrieved document:\n" + readable_output)
