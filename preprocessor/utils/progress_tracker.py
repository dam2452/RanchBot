from contextlib import contextmanager
import time
from typing import Optional

from preprocessor.utils.console import console
from preprocessor.utils.time_utils import (
    format_time_hms,
    format_time_human,
)


class ProgressTracker:
    def __init__(self):
        self.current_operation: Optional[str] = None
        self.start_time: Optional[float] = None

    @contextmanager
    def track_operation(self, operation_name: str, total: int):
        self.current_operation = operation_name
        self.start_time = time.time()
        console.print(f"  [cyan]{operation_name} (total: {total})...[/cyan]")

        tracker = OperationTracker(
            operation_name=operation_name,
            total=total,
            start_time=self.start_time,
        )

        try:
            yield tracker
        finally:
            if tracker.completed > 0:
                elapsed = time.time() - self.start_time
                console.print(
                    f"  [green]✓ {operation_name} completed: "
                    f"{tracker.completed}/{total} in {format_time_human(elapsed)}[/green]",
                )


class OperationTracker:
    def __init__(self, operation_name: str, total: int, start_time: float):
        self.operation_name = operation_name
        self.total = total
        self.completed = 0
        self.start_time = start_time
        self.last_report = 0

    def update(self, completed: int, interval: int = 10):
        self.completed = completed

        should_report = (
            completed % interval == 0 or
            completed == self.total or
            completed == 1
        )

        if should_report and completed != self.last_report:
            self.__report_progress()
            self.last_report = completed

    def __report_progress(self):
        elapsed = time.time() - self.start_time
        percent = (self.completed / self.total * 100) if self.total > 0 else 0

        if 0 < self.completed < self.total:
            rate = self.completed / elapsed if elapsed > 0 else 0
            remaining = self.total - self.completed
            eta_seconds = remaining / rate if rate > 0 else 0
            eta = format_time_hms(eta_seconds) if eta_seconds > 0 else "0:00:00"
        elif self.completed >= self.total:
            eta = "0:00:00"
        else:
            eta = "-:--:--"

        console.print(
            f"    [dim]{self.operation_name}: {self.completed}/{self.total} "
            f"({percent:.0f}%) ETA: {eta}[/dim]",
        )
