# pylint: disable=too-many-arguments,too-many-locals,too-many-branches,too-many-statements
import asyncio
import json
from pathlib import Path
import sys

import click
from elasticsearch import AsyncElasticsearch

from preprocessor.search import (
    ElasticsearchQueries,
    EmbeddingService,
    HashService,
    ResultFormatter,
)


@click.command(context_settings={"show_default": True})
@click.option("--text", type=str, help="Full-text search po transkrypcjach")
@click.option("--text-semantic", type=str, help="Semantic search po text embeddings")
@click.option("--text-to-video", type=str, help="Cross-modal search: text query w video embeddings")
@click.option("--image", type=click.Path(exists=True, path_type=Path), help="Semantic search po video embeddings")
@click.option("--hash", "phash", type=str, help="Szukaj po perceptual hash (podaj hash string lub sciezke do obrazka)")
@click.option("--character", type=str, help="Szukaj po postaci")
@click.option("--emotion", type=str, help="Szukaj po emocji (neutral, happiness, surprise, sadness, anger, disgust, fear, contempt)")
@click.option("--object", "object_query", type=str, help="Szukaj po wykrytych obiektach (np. 'dog', 'person:5+', 'chair:2-4')")
@click.option("--episode-name", type=str, help="Fuzzy search po nazwach odcinkow")
@click.option("--episode-name-semantic", type=str, help="Semantic search po nazwach odcinkow")
@click.option("--list-characters", "list_chars_flag", is_flag=True, help="Lista wszystkich postaci")
@click.option("--list-objects", "list_objects_flag", is_flag=True, help="Lista wszystkich klas obiektow")
@click.option("--season", type=int, help="Filtruj po sezonie")
@click.option("--episode", type=int, help="Filtruj po odcinku")
@click.option("--limit", type=int, default=20, help="Limit wynikow")
@click.option("--stats", is_flag=True, help="Pokaz statystyki indeksow")
@click.option("--json-output", is_flag=True, help="Output w formacie JSON")
@click.option("--host", type=str, default="http://localhost:9200", help="Elasticsearch host")
def search(
    text, text_semantic, text_to_video, image, phash, character, emotion, object_query, episode_name,
    episode_name_semantic, list_chars_flag, list_objects_flag, season, episode, limit,
    stats, json_output, host,
):
    """Search tool - comprehensive Elasticsearch search"""

    if not any([
        text, text_semantic, text_to_video, image, phash, character, emotion,
        object_query, episode_name, episode_name_semantic, list_chars_flag, list_objects_flag, stats,
    ]):
        click.echo("Podaj przynajmniej jedna opcje wyszukiwania. Uzyj --help", err=True)
        sys.exit(1)

    embedding_service = EmbeddingService()
    hash_service = HashService()
    queries = ElasticsearchQueries(embedding_service)

    hash_value = None
    if phash:
        phash_path = Path(phash)
        if phash_path.exists() and phash_path.is_file():
            click.echo(f"Computing perceptual hash from image: {phash}", err=True)
            hash_value = hash_service.get_perceptual_hash(str(phash_path))
            if hash_value:
                click.echo(f"Computed hash: {hash_value}", err=True)
            else:
                click.echo("Failed to compute hash from image", err=True)
                sys.exit(1)
        else:
            hash_value = phash

    async def __run():
        es_client = AsyncElasticsearch(hosts=[host], verify_certs=False)

        try:
            await es_client.ping()
        except Exception:
            click.echo(f"✗ Cannot connect to Elasticsearch at {host}", err=True)
            click.echo("Make sure Elasticsearch is running:", err=True)
            click.echo("  docker-compose -f docker-compose.test.yml up -d", err=True)
            sys.exit(1)

        try:
            if stats:
                result = await queries.get_stats(es_client)
                if json_output:
                    click.echo(json.dumps(result, indent=2))
                else:
                    click.echo("\nStatystyki:")
                    click.echo(f"  Segments: {result['segments']:,}")
                    click.echo(f"  Text Embeddings: {result['text_embeddings']:,}")
                    click.echo(f"  Video Embeddings: {result['video_embeddings']:,}")
                    click.echo(f"  Episode Names: {result['episode_names']:,}")

            elif list_chars_flag:
                chars = await queries.list_characters(es_client)
                if json_output:
                    click.echo(json.dumps(chars, indent=2))
                else:
                    click.echo(f"\nZnaleziono {len(chars)} postaci:")
                    for char, count in sorted(chars, key=lambda x: -x[1]):
                        click.echo(f"  {char}: {count:,} wystapien")

            elif list_objects_flag:
                objects = await queries.list_objects(es_client)
                if json_output:
                    click.echo(json.dumps(objects, indent=2))
                else:
                    click.echo(f"\nZnaleziono {len(objects)} klas obiektow:")
                    for obj, count in sorted(objects, key=lambda x: -x[1]):
                        click.echo(f"  {obj}: {count:,} wystapien")

            elif text:
                result = await queries.search_text_query(es_client, text, season, episode, limit)
                if json_output:
                    click.echo(json.dumps(result["hits"], indent=2))
                else:
                    ResultFormatter.print_results(result, "text")

            elif text_semantic:
                result = await queries.search_text_semantic(es_client, text_semantic, season, episode, limit)
                if json_output:
                    click.echo(json.dumps(result["hits"], indent=2))
                else:
                    ResultFormatter.print_results(result, "text_semantic")

            elif text_to_video:
                result = await queries.search_text_to_video(es_client, text_to_video, season, episode, character, limit)
                if json_output:
                    click.echo(json.dumps(result["hits"], indent=2))
                else:
                    ResultFormatter.print_results(result, "video")

            elif image:
                result = await queries.search_video_semantic(es_client, str(image), season, episode, character, limit)
                if json_output:
                    click.echo(json.dumps(result["hits"], indent=2))
                else:
                    ResultFormatter.print_results(result, "video")

            elif emotion:
                result = await queries.search_by_emotion(es_client, emotion, season, episode, character, limit)
                if json_output:
                    click.echo(json.dumps(result["hits"], indent=2))
                else:
                    ResultFormatter.print_results(result, "video")

            elif character:
                result = await queries.search_by_character(es_client, character, season, episode, limit)
                if json_output:
                    click.echo(json.dumps(result["hits"], indent=2))
                else:
                    ResultFormatter.print_results(result, "video")

            elif object_query:
                result = await queries.search_by_object(es_client, object_query, season, episode, limit)
                if json_output:
                    click.echo(json.dumps(result["hits"], indent=2))
                else:
                    ResultFormatter.print_results(result, "video")

            elif hash_value:
                result = await queries.search_perceptual_hash(es_client, hash_value, limit)
                if json_output:
                    click.echo(json.dumps(result["hits"], indent=2))
                else:
                    ResultFormatter.print_results(result, "video")

            elif episode_name:
                result = await queries.search_episode_name(es_client, episode_name, season, limit)
                if json_output:
                    click.echo(json.dumps(result["hits"], indent=2))
                else:
                    ResultFormatter.print_results(result, "episode_name")

            elif episode_name_semantic:
                result = await queries.search_episode_name_semantic(es_client, episode_name_semantic, season, limit)
                if json_output:
                    click.echo(json.dumps(result["hits"], indent=2))
                else:
                    ResultFormatter.print_results(result, "episode_name")

        finally:
            await es_client.close()

    asyncio.run(__run())
