from pathlib import Path
from typing import Callable

import click

from preprocessor.app.pipeline_builder import Pipeline as PipelineRunner
from preprocessor.app.pipeline_factory import (
    build_pipeline,
    visualize,
)
from preprocessor.cli.helpers import setup_pipeline_context


@click.group()
@click.help_option("-h", "--help")
def cli() -> None:
    pass


@cli.command(name="visualize")
def visualize_command() -> None:
    visualize()


@cli.command(name="run-all")
@click.option("--series", required=True, help="Series name (e.g., ranczo)")
@click.option("--force-rerun", is_flag=True, help="Force rerun even if cached")
@click.option(
    "--skip",
    multiple=True,
    help="Step IDs to skip (e.g., --skip transcode --skip detect_scenes)",
)
def run_all(series: str, force_rerun: bool, skip: tuple) -> None:
    pipeline = build_pipeline()
    setup = setup_pipeline_context(series, "run_all", force_rerun, with_episode_manager=True)

    plan = pipeline.get_execution_order(skip=list(skip))

    setup.logger.info(f"📋 Execution plan: {' → '.join(plan)}")
    setup.logger.info(f"📂 Source: preprocessor/input_data/{series}")

    source_path = Path("preprocessor/input_data") / series

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


def _create_step_command(step_id: str, step_description: str) -> Callable:
    @click.command(name=step_id.replace("_", "-"), help=f"{step_description}")
    @click.option("--series", required=True, help="Series name (e.g., ranczo)")
    @click.option("--force-rerun", is_flag=True, help="Force rerun even if cached")
    def step_command(series: str, force_rerun: bool, _step_id: str = step_id) -> None:
        pipeline = build_pipeline()
        setup = setup_pipeline_context(series, _step_id, force_rerun, with_episode_manager=True)

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

        source_path = Path("preprocessor/input_data") / series

        runner = PipelineRunner(setup.context)
        runner.add_step(instance)
        runner.run_for_episodes(source_path, setup.episode_manager)

        setup.logger.info(f"✅ Step '{_step_id}' completed successfully")

    return step_command


_cli_pipeline = build_pipeline()

for _step_id, _step in _cli_pipeline._steps.items():
    command_func = _create_step_command(_step_id, _step.description)
    cli.add_command(command_func)


if __name__ == "__main__":
    cli()
