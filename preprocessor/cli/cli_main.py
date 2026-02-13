import asyncio
from pathlib import Path
import sys
from typing import Tuple

import click
from click import Command
from elasticsearch import AsyncElasticsearch

from preprocessor.app.pipeline_builder import PipelineExecutor
from preprocessor.app.pipeline_factory import (
    build_pipeline,
    visualize,
)
from preprocessor.cli.helpers import setup_pipeline_context
from preprocessor.cli.search_handler import (
    SearchCommandHandler,
    SearchFilters,
)
from preprocessor.cli.search_params import (
    SearchActionParams,
    SearchConfig,
    SearchQueryParams,
)
from preprocessor.cli.skip_list_builder import SkipListBuilder
from preprocessor.config.series_config import SeriesConfig
from preprocessor.services.io.path_service import PathService
from preprocessor.services.search.clients.elasticsearch_queries import ElasticsearchQueries
from preprocessor.services.search.clients.embedding_service import EmbeddingService


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

        source_path = PathService.get_input_base() / series

        setup.logger.info(f"Execution plan: {' -> '.join(plan)}")
        setup.logger.info(f"Source: {source_path}")

        executor = PipelineExecutor(setup.context)
        executor.execute_steps(
            pipeline=pipeline,
            step_ids=plan,
            source_path=source_path,
            episode_manager=setup.episode_manager,
        )

        setup.logger.info("=" * 80)
        setup.logger.info("Pipeline completed successfully!")
    except KeyboardInterrupt:
        setup.logger.info("\nInterrupted by user")
        raise
    finally:
        setup.logger.finalize()


def __create_step_command(step_id: str, step_description: str) -> Command:
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
                setup.logger.info(f"Dependencies: {', '.join(deps)}")
                for dep_id in deps:
                    if not setup.context.state_manager.is_step_completed(dep_id, "*"):
                        setup.logger.warning(
                            f"Dependency '{dep_id}' may not be completed. "
                            f"Run it first or use --force-rerun.",
                        )

            source_path = PathService.get_input_base() / series

            executor = PipelineExecutor(setup.context)
            executor.execute_step(
                pipeline=pipeline,
                step_id=_step_id,
                source_path=source_path,
                episode_manager=setup.episode_manager,
            )

            setup.logger.info(f"Step '{_step_id}' completed successfully")
        except KeyboardInterrupt:
            setup.logger.info("\nInterrupted by user")
            raise
        finally:
            setup.logger.finalize()

    return __step_command


@cli.command(name="analyze-resolution")
@click.option("--series", required=True, help="Series name (e.g., ranczo, kiepscy)")
def __analyze_resolution(series: str) -> None:
    pipeline = build_pipeline(series)
    setup = setup_pipeline_context(series, "resolution_analysis", False, with_episode_manager=False)

    try:
        step = pipeline.get_step("resolution_analysis")
        step.execute(None, setup.context)

        setup.logger.info("Resolution analysis completed")
    except KeyboardInterrupt:
        setup.logger.info("\nInterrupted by user")
        raise
    finally:
        setup.logger.finalize()


def __execute_search_command(config: SearchConfig) -> None:  # pylint: disable=too-many-statements
    series_config = SeriesConfig.load(config.series)
    index_base = series_config.indexing.elasticsearch.index_name

    hash_value = None
    if config.query.phash:
        hash_value = SearchCommandHandler.compute_perceptual_hash(config.query.phash)
        if hash_value is None:
            sys.exit(1)

    async def __run_async_search() -> None:
        es_client = AsyncElasticsearch(hosts=[config.host], verify_certs=False)

        try:
            await es_client.ping()
        except Exception:
            click.echo(f"Cannot connect to Elasticsearch at {config.host}", err=True)
            click.echo("Make sure Elasticsearch is running:", err=True)
            click.echo("  docker-compose -f docker-compose.test.yml up -d", err=True)
            sys.exit(1)

        embedding_svc = EmbeddingService()
        queries = ElasticsearchQueries(embedding_svc, index_base)

        try:
            handler = SearchCommandHandler(es_client, embedding_svc, queries, config.json_output)

            result = None
            if config.actions.stats:
                result = await handler.handle_stats()
            elif config.actions.list_chars_flag:
                result = await handler.handle_list_characters()
            elif config.actions.list_objects_flag:
                result = await handler.handle_list_objects()
            elif config.query.text:
                result = await handler.handle_text_search(config.query.text, config.filters)
            elif config.query.text_semantic:
                result = await handler.handle_text_semantic_search(config.query.text_semantic, config.filters)
            elif config.query.text_to_video:
                result = await handler.handle_text_to_video_search(config.query.text_to_video, config.filters)
            elif config.query.image:
                result = await handler.handle_image_search(config.query.image, config.filters)
            elif config.query.emotion:
                result = await handler.handle_emotion_search(config.query.emotion, config.filters)
            elif config.query.character:
                result = await handler.handle_character_search(config.query.character, config.filters)
            elif config.query.object_query:
                result = await handler.handle_object_search(config.query.object_query, config.filters)
            elif hash_value:
                result = await handler.handle_hash_search(hash_value, config.filters)
            elif config.query.episode_name:
                result = await handler.handle_episode_name_search(config.query.episode_name, config.filters)
            elif config.query.episode_name_semantic:
                result = await handler.handle_episode_name_semantic_search(
                    config.query.episode_name_semantic, config.filters,
                )

            if result:
                click.echo(result)

        finally:
            embedding_svc.cleanup()
            await es_client.close()

    asyncio.run(__run_async_search())


@cli.command(name="search")
@click.option("--series", required=True, help="Series name (e.g., ranczo, kiepscy)")
@click.option("--text", type=str, help="Full-text search by transcriptions")
@click.option("--text-semantic", type=str, help="Semantic search by text embeddings")
@click.option("--text-to-video", type=str, help="Cross-modal search: text query in video embeddings")
@click.option("--image", type=click.Path(exists=True, path_type=Path), help="Semantic search by video embeddings")
@click.option("--hash", "phash", type=str, help="Search by perceptual hash (provide hash string or image path)")
@click.option("--character", type=str, help="Search by character")
@click.option(
    "--emotion", type=str,
    help="Search by emotion (neutral, happiness, surprise, sadness, anger, disgust, fear, contempt)",
)
@click.option(
    "--object", "object_query", type=str,
    help="Search by detected objects (e.g., 'dog', 'person:5+', 'chair:2-4')",
)
@click.option("--episode-name", type=str, help="Fuzzy search by episode names")
@click.option("--episode-name-semantic", type=str, help="Semantic search by episode names")
@click.option("--list-characters", "list_chars_flag", is_flag=True, help="List all characters")
@click.option("--list-objects", "list_objects_flag", is_flag=True, help="List all object classes")
@click.option("--season", type=int, help="Filter by season")
@click.option("--episode", type=int, help="Filter by episode")
@click.option("--limit", type=int, default=20, help="Result limit")
@click.option("--stats", is_flag=True, help="Show index statistics")
@click.option("--json-output", is_flag=True, help="Output in JSON format")
@click.option("--host", type=str, default="http://localhost:9200", help="Elasticsearch host")
def search(  # pylint: disable=too-many-arguments,too-many-locals
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
    config = SearchConfig(
        series=series,
        query=SearchQueryParams(
            text=text,
            text_semantic=text_semantic,
            text_to_video=text_to_video,
            image=image,
            phash=phash,
            character=character,
            emotion=emotion,
            object_query=object_query,
            episode_name=episode_name,
            episode_name_semantic=episode_name_semantic,
        ),
        filters=SearchFilters(season, episode, character, limit),
        actions=SearchActionParams(list_chars_flag, list_objects_flag, stats),
        json_output=json_output,
        host=host,
    )

    if not config.has_any_operation():
        click.echo("Provide at least one search option. Use --help", err=True)
        sys.exit(1)

    __execute_search_command(config)


_CLI_TEMPLATE_SERIES = "ranczo"
_cli_pipeline = build_pipeline(_CLI_TEMPLATE_SERIES)

for _step_id, _step in _cli_pipeline.get_all_steps().items():
    command_func = __create_step_command(_step_id, _step.description)
    cli.add_command(command_func)

if __name__ == "__main__":
    cli()
