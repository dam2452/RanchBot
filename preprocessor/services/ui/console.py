import os
import sys
import time
from typing import (
    Any,
    Dict,
    Optional,
)

from rich.console import Console

from preprocessor.services.core.time import TimeFormatter

_console_instance: Optional[Console] = None


def __get_console() -> Console:
    global _console_instance  # pylint: disable=global-statement
    if _console_instance is None:
        _console_instance = __initialize_rich_console()
    return _console_instance


def __initialize_rich_console() -> Console:
    in_docker = (
            os.path.exists('/.dockerenv') or
            os.getenv('DOCKER_CONTAINER', 'false') == 'true'
    )
    return Console(
        force_terminal=True,
        file=sys.stderr,
        color_system='standard' if in_docker else 'auto',
    )


class SimpleProgress:
    def __init__(self) -> None:
        self.__tasks: Dict[int, Dict[str, Any]] = {}
        self.__task_counter = 0
        self.__console = console

    def __enter__(self) -> 'SimpleProgress':
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.__tasks.clear()

    def add_task(self, description: str, total: int) -> int:
        task_id = self.__task_counter
        self.__task_counter += 1

        self.__tasks[task_id] = {
            'description': description,
            'total': total,
            'completed': 0,
            'start_time': time.time(),
            'last_print_time': 0.0,
        }

        self.__render_progress(task_id)
        return task_id

    def advance(self, task_id: int, step: int = 1) -> None:
        task = self.__tasks.get(task_id)
        if not task:
            return

        task['completed'] += step
        current_time = time.time()

        if self.__should_render(task, current_time):
            self.__render_progress(task_id)
            task['last_print_time'] = current_time

    def __should_render(self, task: Dict[str, Any], current_time: float) -> bool:
        is_finished = task['completed'] >= task['total']
        is_second_passed = (current_time - task['last_print_time']) >= 1.0
        return is_finished or is_second_passed

    def __render_progress(self, task_id: int) -> None:
        task = self.__tasks[task_id]
        completed = task['completed']
        total = task['total']

        percent = (completed / total * 100) if total > 0 else 0
        eta = self.__compute_task_eta(task)
        progress_bar = self.__build_visual_bar(completed, total)

        self.__console.print(
            f"[bold blue]{task['description']}[/bold blue] "
            f"[cyan]{progress_bar}[/cyan] "
            f"[green]{percent:3.0f}%[/green] "
            f"[yellow]{completed}/{total}[/yellow] "
            f"[dim]ETA: {eta}[/dim]",
            highlight=False,
        )

    def __compute_task_eta(self, task: Dict[str, Any]) -> str:
        completed = task['completed']
        total = task['total']

        if completed >= total:
            return '0:00:00'
        if completed <= 0:
            return '-:--:--'

        elapsed = time.time() - task['start_time']
        eta_seconds = (elapsed / completed) * (total - completed)
        return TimeFormatter.format_hms(eta_seconds)

    def __build_visual_bar(self, completed: int, total: int, width: int = 30) -> str:
        if total <= 0:
            return '-' * width

        filled_length = int(width * completed / total)
        if filled_length < width:
            return '=' * filled_length + '>' + '-' * (width - filled_length - 1)
        return '=' * width


def create_progress() -> SimpleProgress:
    return SimpleProgress()


console = __get_console()
