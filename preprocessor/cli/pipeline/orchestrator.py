from dataclasses import dataclass
from typing import (
    Callable,
    List,
    Optional,
)

from preprocessor.cli_utils.resource_scope import ResourceScope
from preprocessor.core.state_manager import StateManager
from preprocessor.utils.console import console


@dataclass
class PipelineStep:
    name: str
    step_num: str
    execute_func: Callable
    skip: bool = False


class PipelineOrchestrator:
    def __init__(self, state_manager: Optional[StateManager] = None):
        self.state_manager = state_manager
        self.steps: List[PipelineStep] = []

    def add_step(self, name: str, step_num: str, func: Callable, skip: bool = False):
        self.steps.append(PipelineStep(name, step_num, func, skip))

    def execute(self, **params) -> int:
        for step in self.steps:
            if step.skip:
                console.print(f"[yellow]Step {step.step_num}: {step.name} - SKIPPED[/yellow]")
                continue

            console.print(f"[bold blue]Step {step.step_num}: {step.name}[/bold blue]")

            with ResourceScope():
                exit_code = step.execute_func(**params)

            if exit_code != 0:
                console.print(f"[red]Step {step.step_num} failed with exit code {exit_code}[/red]")
                return exit_code

        if self.state_manager:
            self.state_manager.cleanup()

        return 0
