from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

import click
from elasticsearch import AsyncElasticsearch

from preprocessor.services.search.clients.elasticsearch_queries import ElasticsearchQueries
from preprocessor.services.search.clients.embedding_service import EmbeddingService
from preprocessor.services.search.clients.hash_service import HashService
from preprocessor.services.search.clients.result_formatters import ResultFormatter


class SearchFilters:

    def __init__(
        self,
        season: Optional[int] = None,
        episode: Optional[int] = None,
        character: Optional[str] = None,
        limit: int = 20,
    ) -> None:
        self.season = season
        self.episode = episode
        self.character = character
        self.limit = limit


class SearchCommandHandler:

    def __init__(
        self,
        es_client: AsyncElasticsearch,
        embedding_service: EmbeddingService,
        queries: ElasticsearchQueries,
        json_output: bool,
    ) -> None:
        self._es = es_client
        self._embedding = embedding_service
        self._queries = queries
        self._json_output = json_output

    async def handle_stats(self) -> str:
        import json  # pylint: disable=import-outside-toplevel

        result = await self._queries.get_stats(self._es)
        if self._json_output:
            return json.dumps(result, indent=2)

        output = ["\nStatystyki:"]
        output.append(f"  Segments: {result['segments']:,}")
        output.append(f"  Text Embeddings: {result['text_embeddings']:,}")
        output.append(f"  Video Embeddings: {result['video_embeddings']:,}")
        output.append(f"  Episode Names: {result['episode_names']:,}")
        return "\n".join(output)

    async def handle_list_characters(self) -> str:
        import json  # pylint: disable=import-outside-toplevel

        chars = await self._queries.list_characters(self._es)
        if self._json_output:
            return json.dumps(chars, indent=2)

        output = [f"\nZnaleziono {len(chars)} postaci:"]
        for char_name, count in sorted(chars, key=lambda x: -x[1]):
            output.append(f"  {char_name}: {count:,} wystapien")
        return "\n".join(output)

    async def handle_list_objects(self) -> str:
        import json  # pylint: disable=import-outside-toplevel

        objects = await self._queries.list_objects(self._es)
        if self._json_output:
            return json.dumps(objects, indent=2)

        output = [f"\nZnaleziono {len(objects)} klas obiektow:"]
        for obj_name, count in sorted(objects, key=lambda x: -x[1]):
            output.append(f"  {obj_name}: {count:,} wystapien")
        return "\n".join(output)

    async def handle_text_search(self, query: str, filters: SearchFilters) -> str:
        import json  # pylint: disable=import-outside-toplevel

        result = await self._queries.search_text_query(
            self._es, query, filters.season, filters.episode, filters.limit,
        )
        if self._json_output:
            return json.dumps(result["hits"], indent=2)

        return self._format_console_output(result, "text")

    async def handle_text_semantic_search(self, query: str, filters: SearchFilters) -> str:
        import json  # pylint: disable=import-outside-toplevel

        result = await self._queries.search_text_semantic(
            self._es, query, filters.season, filters.episode, filters.limit,
        )
        if self._json_output:
            return json.dumps(result["hits"], indent=2)

        return self._format_console_output(result, "text_semantic")

    async def handle_text_to_video_search(self, query: str, filters: SearchFilters) -> str:
        import json  # pylint: disable=import-outside-toplevel

        result = await self._queries.search_text_to_video(
            self._es, query, filters.season, filters.episode, filters.character, filters.limit,
        )
        if self._json_output:
            return json.dumps(result["hits"], indent=2)

        return self._format_console_output(result, "video")

    async def handle_image_search(self, image_path: Path, filters: SearchFilters) -> str:
        import json  # pylint: disable=import-outside-toplevel

        result = await self._queries.search_video_semantic(
            self._es, str(image_path), filters.season, filters.episode, filters.character, filters.limit,
        )
        if self._json_output:
            return json.dumps(result["hits"], indent=2)

        return self._format_console_output(result, "video")

    async def handle_emotion_search(self, emotion: str, filters: SearchFilters) -> str:
        import json  # pylint: disable=import-outside-toplevel

        result = await self._queries.search_by_emotion(
            self._es, emotion, filters.season, filters.episode, filters.character, filters.limit,
        )
        if self._json_output:
            return json.dumps(result["hits"], indent=2)

        return self._format_console_output(result, "video")

    async def handle_character_search(self, character: str, filters: SearchFilters) -> str:
        import json  # pylint: disable=import-outside-toplevel

        result = await self._queries.search_by_character(
            self._es, character, filters.season, filters.episode, filters.limit,
        )
        if self._json_output:
            return json.dumps(result["hits"], indent=2)

        return self._format_console_output(result, "video")

    async def handle_object_search(self, object_query: str, filters: SearchFilters) -> str:
        import json  # pylint: disable=import-outside-toplevel

        result = await self._queries.search_by_object(
            self._es, object_query, filters.season, filters.episode, filters.limit,
        )
        if self._json_output:
            return json.dumps(result["hits"], indent=2)

        return self._format_console_output(result, "video")

    async def handle_hash_search(self, hash_value: str, filters: SearchFilters) -> str:
        import json  # pylint: disable=import-outside-toplevel

        result = await self._queries.search_perceptual_hash(self._es, hash_value, filters.limit)
        if self._json_output:
            return json.dumps(result["hits"], indent=2)

        return self._format_console_output(result, "video")

    async def handle_episode_name_search(self, episode_name: str, filters: SearchFilters) -> str:
        import json  # pylint: disable=import-outside-toplevel

        result = await self._queries.search_episode_name(
            self._es, episode_name, filters.season, filters.limit,
        )
        if self._json_output:
            return json.dumps(result["hits"], indent=2)

        return self._format_console_output(result, "episode_name")

    async def handle_episode_name_semantic_search(self, episode_name: str, filters: SearchFilters) -> str:
        import json  # pylint: disable=import-outside-toplevel

        result = await self._queries.search_episode_name_semantic(
            self._es, episode_name, filters.season, filters.limit,
        )
        if self._json_output:
            return json.dumps(result["hits"], indent=2)

        return self._format_console_output(result, "episode_name")

    @staticmethod
    def compute_perceptual_hash(phash_input: str) -> Optional[str]:
        phash_path = Path(phash_input)
        if phash_path.exists() and phash_path.is_file():
            click.echo(f"Computing perceptual hash from image: {phash_input}", err=True)
            hash_svc = HashService()
            hash_value = hash_svc.get_perceptual_hash(str(phash_path))
            if hash_value:
                click.echo(f"Computed hash: {hash_value}", err=True)
            else:
                click.echo("Failed to compute hash from image", err=True)
                return None
            hash_svc.cleanup()
            return hash_value
        return phash_input

    @staticmethod
    def _format_console_output(result: Dict[str, Any], result_type: str) -> str:
        class __StringBuffer:
            def __init__(self) -> None:
                self.buffer: List[str] = []

            def write(self, text: str) -> None:
                self.buffer.append(text)

            def getvalue(self) -> str:
                return ''.join(self.buffer)

        buffer = __StringBuffer()

        original_echo = click.echo

        def __buffer_echo(message: Optional[str] = None, **_kwargs: Any) -> None:
            if message is not None:
                buffer.write(str(message) + '\n')

        click.echo = __buffer_echo
        try:
            ResultFormatter.print_results(result, result_type)
        finally:
            click.echo = original_echo

        return buffer.getvalue().rstrip()
