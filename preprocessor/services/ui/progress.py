import time
from typing import Optional

from preprocessor.services.core.time import TimeFormatter
from preprocessor.services.ui.console import console


class ProgressTracker:

    def __init__(self) -> None:
        self.current_operation: Optional[str] = None
        self.start_time: Optional[float] = None

class OperationTracker:

    def __init__(self, operation_name: str, total: int, start_time: float) -> None:
        self.operation_name = operation_name
        self.total = total
        self.completed = 0
        self.start_time = start_time
        self.last_report = 0

    def update(self, completed: int, interval: int=10) -> None:
        self.completed = completed
        should_report = completed % interval == 0 or completed == self.total or completed == 1
        if should_report and completed != self.last_report:
            self.__report_progress()
            self.last_report = completed

    def __report_progress(self) -> None:
        elapsed = time.time() - self.start_time
        percent = self.completed / self.total * 100 if self.total > 0 else 0
        if 0 < self.completed < self.total:
            rate = self.completed / elapsed if elapsed > 0 else 0
            remaining = self.total - self.completed
            eta_seconds = remaining / rate if rate > 0 else 0
            eta = TimeFormatter.format_hms(eta_seconds) if eta_seconds > 0 else '0:00:00'
        elif self.completed >= self.total:
            eta = '0:00:00'
        else:
            eta = '-:--:--'
        console.print(f'    [dim]{self.operation_name}: {self.completed}/{self.total} ({percent:.0f}%) ETA: {eta}[/dim]')
