from contextlib import contextmanager
import time
from typing import Optional

from preprocessor.utils.console import console


class ProgressTracker:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.current_operation: Optional[str] = None
        self.start_time: Optional[float] = None

    @contextmanager
    def track_operation(self, operation_name: str, total: int):
        if self.enabled:
            self.current_operation = operation_name
            self.start_time = time.time()
            console.print(f"  [cyan]{operation_name} (total: {total})...[/cyan]")

        tracker = OperationTracker(
            operation_name=operation_name,
            total=total,
            enabled=self.enabled,
            start_time=self.start_time,
        )

        try:
            yield tracker
        finally:
            if self.enabled and tracker.completed > 0:
                elapsed = time.time() - self.start_time
                console.print(
                    f"  [green]✓ {operation_name} completed: "
                    f"{tracker.completed}/{total} in {self._format_time(elapsed)}[/green]",
                )

    @staticmethod
    def _format_time(seconds: float) -> str:
        if seconds < 60:
            return f"{seconds:.1f}s"
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        if minutes < 60:
            return f"{minutes}m {secs}s"
        hours = minutes // 60
        minutes = minutes % 60
        return f"{hours}h {minutes}m {secs}s"


class OperationTracker:
    def __init__(self, operation_name: str, total: int, enabled: bool, start_time: float):
        self.operation_name = operation_name
        self.total = total
        self.completed = 0
        self.enabled = enabled
        self.start_time = start_time
        self.last_report = 0

    def update(self, completed: int, interval: int = 10):
        self.completed = completed

        if not self.enabled:
            return

        should_report = (
            completed % interval == 0 or
            completed == self.total or
            completed == 1
        )

        if should_report and completed != self.last_report:
            self._report_progress()
            self.last_report = completed

    def _report_progress(self):
        elapsed = time.time() - self.start_time
        percent = (self.completed / self.total * 100) if self.total > 0 else 0

        if self.completed > 0 and self.completed < self.total:
            rate = self.completed / elapsed if elapsed > 0 else 0
            remaining = self.total - self.completed
            eta_seconds = remaining / rate if rate > 0 else 0
            eta = self._format_eta(eta_seconds)
        elif self.completed >= self.total:
            eta = "0:00:00"
        else:
            eta = "-:--:--"

        console.print(
            f"    [dim]{self.operation_name}: {self.completed}/{self.total} "
            f"({percent:.0f}%) ETA: {eta}[/dim]",
        )

    @staticmethod
    def _format_eta(seconds: float) -> str:
        if seconds <= 0:
            return "0:00:00"
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours}:{minutes:02d}:{secs:02d}"
