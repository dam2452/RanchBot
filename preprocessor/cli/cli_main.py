from pathlib import Path
from typing import (
    Callable,
    Tuple,
)

import click

from preprocessor.app.pipeline_builder import PipelineExecutor
from preprocessor.app.pipeline_factory import (
    build_pipeline,
    visualize,
)
from preprocessor.cli.helpers import setup_pipeline_context
from preprocessor.cli.skip_list_builder import SkipListBuilder
from preprocessor.config.series_config import SeriesConfig
from preprocessor.lib.io.path_resolver import PathResolver


@click.group()
@click.help_option("-h", "--help")
def cli() -> None:
    pass


@cli.command(name="visualize")
@click.option("--series", default="ranczo", help="Series name (e.g., ranczo)")
def __visualize_command(series: str) -> None:
    visualize(series)


@cli.command(name="run-all")
@click.option("--series", required=True, help="Series name (e.g., ranczo)")
@click.option("--force-rerun", is_flag=True, help="Force rerun even if cached")
@click.option(
    "--skip",
    multiple=True,
    help="Step IDs to skip (e.g., --skip transcode --skip detect_scenes)",
)
def __run_all(series: str, force_rerun: bool, skip: Tuple[str, ...]) -> None:
    series_config = SeriesConfig.load(series)
    pipeline = build_pipeline(series)
    setup = setup_pipeline_context(series, "__run_all", force_rerun, with_episode_manager=True)

    try:
        skip_list = SkipListBuilder.build(skip, series_config, setup.logger)
        plan = pipeline.get_execution_order(skip=skip_list)

        source_path = PathResolver.get_input_base() / series

        setup.logger.info(f"📋 Execution plan: {' → '.join(plan)}")
        setup.logger.info(f"📂 Source: {source_path}")

        executor = PipelineExecutor(setup.context)
        executor.execute_steps(
            pipeline=pipeline,
            step_ids=plan,
            source_path=source_path,
            episode_manager=setup.episode_manager,
        )

        setup.logger.info("=" * 80)
        setup.logger.info("🎉 Pipeline completed successfully!")
    except KeyboardInterrupt:
        setup.logger.info("\n🛑 Interrupted by user")
        raise
    finally:
        setup.logger.finalize()


def __create_step_command(step_id: str, step_description: str) -> Callable:
    @click.command(name=step_id.replace("_", "-"), help=f"{step_description}")
    @click.option("--series", required=True, help="Series name (e.g., ranczo)")
    @click.option("--force-rerun", is_flag=True, help="Force rerun even if cached")
    def __step_command(series: str, force_rerun: bool, _step_id: str = step_id) -> None:
        pipeline = build_pipeline(series)
        setup = setup_pipeline_context(series, _step_id, force_rerun, with_episode_manager=True)

        try:
            step = pipeline.get_step(_step_id)

            deps = step.dependency_ids
            if deps:
                setup.logger.info(f"📦 Dependencies: {', '.join(deps)}")
                for dep_id in deps:
                    if not setup.context.state_manager.is_step_completed(dep_id, "*"):
                        setup.logger.warning(
                            f"⚠️  Dependency '{dep_id}' may not be completed. "
                            f"Run it first or use --force-rerun.",
                        )

            source_path = PathResolver.get_input_base() / series

            executor = PipelineExecutor(setup.context)
            executor.execute_step(
                pipeline=pipeline,
                step_id=_step_id,
                source_path=source_path,
                episode_manager=setup.episode_manager,
            )

            setup.logger.info(f"✅ Step '{_step_id}' completed successfully")
        except KeyboardInterrupt:
            setup.logger.info("\n🛑 Interrupted by user")
            raise
        finally:
            setup.logger.finalize()

    return __step_command


@cli.command(name="search")
@click.option("--series", required=True, help="Series name (e.g., ranczo, kiepscy)")
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
def search(  # pylint: disable=too-many-arguments,too-many-locals,too-many-statements
    series: str,
    text: str,
    text_semantic: str,
    text_to_video: str,
    image: Path,
    phash: str,
    character: str,
    emotion: str,
    object_query: str,
    episode_name: str,
    episode_name_semantic: str,
    list_chars_flag: bool,
    list_objects_flag: bool,
    season: int,
    episode: int,
    limit: int,
    stats: bool,
    json_output: bool,
    host: str,
) -> None:
    import asyncio  # pylint: disable=import-outside-toplevel
    import json  # pylint: disable=import-outside-toplevel
    import sys  # pylint: disable=import-outside-toplevel

    from elasticsearch import AsyncElasticsearch  # pylint: disable=import-outside-toplevel

    from preprocessor.lib.search.clients.elasticsearch_queries import ElasticsearchQueries  # pylint: disable=import-outside-toplevel
    from preprocessor.lib.search.clients.embedding_service import EmbeddingService  # pylint: disable=import-outside-toplevel
    from preprocessor.lib.search.clients.hash_service import HashService  # pylint: disable=import-outside-toplevel
    from preprocessor.lib.search.clients.result_formatters import ResultFormatter  # pylint: disable=import-outside-toplevel

    if not any([
        text, text_semantic, text_to_video, image, phash, character, emotion,
        object_query, episode_name, episode_name_semantic, list_chars_flag, list_objects_flag, stats,
    ]):
        click.echo("Podaj przynajmniej jedna opcje wyszukiwania. Uzyj --help", err=True)
        sys.exit(1)

    series_config = SeriesConfig.load(series)
    index_base = series_config.indexing.elasticsearch.index_name

    hash_value = None
    if phash:
        phash_path = Path(phash)
        if phash_path.exists() and phash_path.is_file():
            click.echo(f"Computing perceptual hash from image: {phash}", err=True)
            hash_svc = HashService()
            hash_value = hash_svc.get_perceptual_hash(str(phash_path))
            if hash_value:
                click.echo(f"Computed hash: {hash_value}", err=True)
            else:
                click.echo("Failed to compute hash from image", err=True)
                sys.exit(1)
            hash_svc.cleanup()
        else:
            hash_value = phash

    async def run() -> None:  # pylint: disable=too-many-branches,too-many-statements
        es_client = AsyncElasticsearch(hosts=[host], verify_certs=False)

        try:
            await es_client.ping()
        except Exception:  # pylint: disable=broad-except
            click.echo(f"✗ Cannot connect to Elasticsearch at {host}", err=True)
            click.echo("Make sure Elasticsearch is running:", err=True)
            click.echo("  docker-compose -f docker-compose.test.yml up -d", err=True)
            sys.exit(1)

        embedding_svc = EmbeddingService()
        queries = ElasticsearchQueries(embedding_svc, index_base)

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
                    for char_name, count in sorted(chars, key=lambda x: -x[1]):
                        click.echo(f"  {char_name}: {count:,} wystapien")

            elif list_objects_flag:
                objects = await queries.list_objects(es_client)
                if json_output:
                    click.echo(json.dumps(objects, indent=2))
                else:
                    click.echo(f"\nZnaleziono {len(objects)} klas obiektow:")
                    for obj_name, count in sorted(objects, key=lambda x: -x[1]):
                        click.echo(f"  {obj_name}: {count:,} wystapien")

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
            embedding_svc.cleanup()
            await es_client.close()

    asyncio.run(run())


_CLI_TEMPLATE_SERIES = "ranczo"
_cli_pipeline = build_pipeline(_CLI_TEMPLATE_SERIES)

for _step_id, _step in _cli_pipeline.get_all_steps().items():
    command_func = __create_step_command(_step_id, _step.description)
    cli.add_command(command_func)


if __name__ == "__main__":
    cli()
