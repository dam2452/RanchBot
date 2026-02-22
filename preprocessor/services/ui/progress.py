import time

from preprocessor.services.core.time import TimeFormatter
from preprocessor.services.ui.console import console


class OperationTracker:
    def __init__(self, operation_name: str, total: int, start_time: float) -> None:
        self.__operation_name = operation_name
        self.__total = total
        self.__completed = 0
        self.__start_time = start_time
        self.__last_report_count = 0

    def update(self, completed: int, interval: int = 10) -> None:
        self.__completed = completed

        if self.__should_report_progress(completed, interval):
            self.__report_progress()
            self.__last_report_count = completed

    def __should_report_progress(self, completed: int, interval: int) -> bool:
        if completed == self.__last_report_count:
            return False

        is_milestone = (completed % interval == 0) or (completed == self.__total) or (completed == 1)
        return is_milestone

    def __report_progress(self) -> None:
        percent = (self.__completed / self.__total * 100) if self.__total > 0 else 0
        eta = self.__calculate_eta()

        console.print(
            f'    [dim]{self.__operation_name}: {self.__completed}/{self.__total} '
            f'({percent:.0f}%) ETA: {eta}[/dim]',
        )

    def __calculate_eta(self) -> str:
        elapsed = time.time() - self.__start_time

        if self.__completed >= self.__total:
            return '0:00:00'

        if self.__completed <= 0:
            return '-:--:--'

        rate = self.__completed / elapsed if elapsed > 0 else 0
        remaining = self.__total - self.__completed
        eta_seconds = remaining / rate if rate > 0 else 0

        return TimeFormatter.format_hms(eta_seconds) if eta_seconds > 0 else '0:00:00'
