from datetime import datetime
from pathlib import Path
from typing import (
    Dict,
    List,
)

from preprocessor.app.pipeline import PipelineDefinition
from preprocessor.core.state_manager import StepCheckpoint
from preprocessor.services.episodes.types import EpisodeInfo
from preprocessor.services.ui.console import console


class StateReconstructor:
    @staticmethod
    def scan_filesystem(
        pipeline: PipelineDefinition,
        episodes_list: List[EpisodeInfo],
        base_output_dir: Path,
        series_name: str,
    ) -> List[StepCheckpoint]:
        console.print('[cyan]Reconstructing state from filesystem...[/cyan]')

        now = datetime.now().isoformat()
        completed_steps: List[StepCheckpoint] = []

        total_checked = 0
        total_completed = 0

        for step_id, step_def in pipeline.get_all_steps().items():
            step_instance = step_def.step_class(step_def.config)
            step_name = step_instance.name

            if step_instance.is_global:
                if StateReconstructor.__check_global_step_outputs(step_instance, base_output_dir):
                    checkpoint = StepCheckpoint(
                        step=step_name,
                        episode='all',
                        completed_at=now,
                    )
                    completed_steps.append(checkpoint)
                    total_completed += 1
                    console.print(f'[green]✓ {step_id} ({step_name}) - global[/green]')
                else:
                    console.print(f'[yellow]✗ {step_id} ({step_name}) - global - outputs missing[/yellow]')
                total_checked += 1
            else:
                for episode_info in episodes_list:
                    episode_id = f'S{episode_info.season:02d}E{episode_info.relative_episode:02d}'
                    context_vars = {
                        'season': episode_info.season_code(),
                        'episode': episode_info.episode_code(),
                        'series_name': series_name,
                    }

                    if StateReconstructor.__check_episode_step_outputs(
                        step_instance, base_output_dir, context_vars,
                    ):
                        checkpoint = StepCheckpoint(
                            step=step_name,
                            episode=episode_id,
                            completed_at=now,
                        )
                        completed_steps.append(checkpoint)
                        total_completed += 1
                    total_checked += 1

        console.print('\n[green]Filesystem scan complete:[/green]')
        console.print(f'  Checked: {total_checked} step-episode combinations')
        console.print(f'  Found completed: {total_completed}')
        console.print(f'  Missing: {total_checked - total_completed}')

        return completed_steps

    @staticmethod
    def __check_global_step_outputs(step_instance, base_output_dir: Path) -> bool:
        descriptors = step_instance._get_output_descriptors()
        if not descriptors:
            return True

        return all(
            descriptor.validate(base_output_dir).is_valid
            for descriptor in descriptors
        )

    @staticmethod
    def __check_episode_step_outputs(
        step_instance,
        base_output_dir: Path,
        context_vars: Dict[str, str],
    ) -> bool:
        descriptors = step_instance._get_output_descriptors()
        if not descriptors:
            return True

        return all(
            descriptor.validate(base_output_dir, context_vars).is_valid
            for descriptor in descriptors
        )
