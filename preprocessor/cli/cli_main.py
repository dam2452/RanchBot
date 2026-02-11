import os
from pathlib import Path
from typing import Callable

import click

from preprocessor.app.pipeline_builder import Pipeline as PipelineRunner
from preprocessor.app.pipeline_factory import (
    build_pipeline,
    visualize,
)
from preprocessor.cli.helpers import setup_pipeline_context
from preprocessor.config.series_config import SeriesConfig


def _get_input_base_path() -> Path:
    is_docker: bool = os.getenv('DOCKER_CONTAINER', 'false').lower() == 'true'
    return Path('/input_data') if is_docker else Path('preprocessor/input_data')


def _get_output_base_path() -> Path:
    is_docker: bool = os.getenv('DOCKER_CONTAINER', 'false').lower() == 'true'
    return Path('/app/output_data') if is_docker else Path('preprocessor/output_data')


@click.group()
@click.help_option("-h", "--help")
def cli() -> None:
    pass


@cli.command(name="visualize")
@click.option("--series", default="ranczo", help="Series name (e.g., ranczo)")
def visualize_command(series: str) -> None:
    visualize(series)


@cli.command(name="run-all")
@click.option("--series", required=True, help="Series name (e.g., ranczo)")
@click.option("--force-rerun", is_flag=True, help="Force rerun even if cached")
@click.option(
    "--skip",
    multiple=True,
    help="Step IDs to skip (e.g., --skip transcode --skip detect_scenes)",
)
def run_all(series: str, force_rerun: bool, skip: tuple) -> None:
    series_config = SeriesConfig.load(series)
    pipeline = build_pipeline(series)
    setup = setup_pipeline_context(series, "run_all", force_rerun, with_episode_manager=True)

    try:  # pylint: disable=too-many-try-statements
        skip_list = list(skip)
        if series_config.pipeline_mode == "selective":
            skip_list.extend(series_config.skip_steps)
            skip_list = list(set(skip_list))
            if series_config.skip_steps:
                setup.logger.info(f"🔧 Selective mode: auto-skipping {', '.join(series_config.skip_steps)}")

        plan = pipeline.get_execution_order(skip=skip_list)

        input_base = _get_input_base_path()
        source_path = input_base / series

        setup.logger.info(f"📋 Execution plan: {' → '.join(plan)}")
        setup.logger.info(f"📂 Source: {source_path}")

        for step_id in plan:
            step = pipeline.get_step(step_id)
            setup.logger.info(f"{'=' * 80}")
            setup.logger.info(f"🔧 Step: {step_id}")
            setup.logger.info(f"📝 {step.description}")

            StepClass = step.load_class()
            instance = StepClass(step.config)

            runner = PipelineRunner(setup.context)
            runner.add_step(instance)
            runner.run_for_episodes(source_path, setup.episode_manager)

            setup.logger.info(f"✅ Step '{step_id}' completed")

        setup.logger.info("=" * 80)
        setup.logger.info("🎉 Pipeline completed successfully!")
    except KeyboardInterrupt:
        setup.logger.info("\n🛑 Interrupted by user")
        raise
    finally:
        setup.logger.finalize()


def _create_step_command(step_id: str, step_description: str) -> Callable:
    @click.command(name=step_id.replace("_", "-"), help=f"{step_description}")
    @click.option("--series", required=True, help="Series name (e.g., ranczo)")
    @click.option("--force-rerun", is_flag=True, help="Force rerun even if cached")
    def step_command(series: str, force_rerun: bool, _step_id: str = step_id) -> None:
        pipeline = build_pipeline(series)
        setup = setup_pipeline_context(series, _step_id, force_rerun, with_episode_manager=True)

        try:  # pylint: disable=too-many-try-statements
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

            setup.logger.info(f"🔧 Running: {_step_id}")
            setup.logger.info(f"📝 {step.description}")

            StepClass = step.load_class()
            instance = StepClass(step.config)

            input_base = _get_input_base_path()
            source_path = input_base / series

            runner = PipelineRunner(setup.context)
            runner.add_step(instance)
            runner.run_for_episodes(source_path, setup.episode_manager)

            setup.logger.info(f"✅ Step '{_step_id}' completed successfully")
        except KeyboardInterrupt:
            setup.logger.info("\n🛑 Interrupted by user")
            raise
        finally:
            setup.logger.finalize()

    return step_command


_cli_pipeline = build_pipeline("ranczo")

for _step_id, _step in _cli_pipeline._steps.items():
    command_func = _create_step_command(_step_id, _step.description)
    cli.add_command(command_func)


if __name__ == "__main__":
    cli()
