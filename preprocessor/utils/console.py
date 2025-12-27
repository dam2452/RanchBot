import os
import sys
import time

from rich.console import Console

from preprocessor.utils.time_utils import format_time_hms

_console_instance = None


def get_console() -> Console:
    global _console_instance  # pylint: disable=global-statement
    if _console_instance is None:
        in_docker = os.path.exists('/.dockerenv') or os.getenv('DOCKER_CONTAINER', 'false') == 'true'

        _console_instance = Console(
            force_terminal=True,
            file=sys.stderr,
            color_system="standard" if in_docker else "auto",
        )
    return _console_instance


class SimpleProgress:
    def __init__(self):
        self.tasks = {}
        self.task_counter = 0
        self.console = console

    def add_task(self, description: str, total: int):
        task_id = self.task_counter
        self.task_counter += 1
        self.tasks[task_id] = {
            'description': description,
            'total': total,
            'completed': 0,
            'start_time': time.time(),
            'last_print': 0,
        }
        self._print_progress(task_id)
        return task_id

    def advance(self, task_id: int, advance: int = 1):
        if task_id not in self.tasks:
            return

        task = self.tasks[task_id]
        task['completed'] += advance

        current_time = time.time()
        if current_time - task['last_print'] >= 1.0 or task['completed'] >= task['total']:
            self._print_progress(task_id)
            task['last_print'] = current_time

    def _print_progress(self, task_id: int):
        task = self.tasks[task_id]
        completed = task['completed']
        total = task['total']
        percent = (completed / total * 100) if total > 0 else 0

        elapsed = time.time() - task['start_time']
        if 0 < completed < total:
            eta_seconds = (elapsed / completed) * (total - completed)
            eta = format_time_hms(eta_seconds)
        elif completed >= total:
            eta = "0:00:00"
        else:
            eta = "-:--:--"

        bar_width = 30
        filled = int(bar_width * completed / total) if total > 0 else 0
        progress_bar = "━" * filled + "╸" + "─" * (bar_width - filled - 1) if filled < bar_width else "━" * bar_width

        console.print(
            f"[bold blue]{task['description']}[/bold blue] "
            f"[cyan]{progress_bar}[/cyan] "
            f"[green]{percent:3.0f}%[/green] "
            f"[yellow]{completed}/{total}[/yellow] "
            f"[dim]ETA: {eta}[/dim]",
            highlight=False,
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


def create_progress() -> SimpleProgress:
    return SimpleProgress()


console = get_console()
