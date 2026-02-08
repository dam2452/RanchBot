from typing import (
    List,
    Optional,
)


class VideoException(Exception):
    pass


class VideoTooLargeException(VideoException):
    def __init__(self, duration: Optional[float] = None, suggestions: Optional[List[str]] = None) -> None:
        self._duration = duration
        self._suggestions = suggestions
        super().__init__(f"Video too large: {duration}s")

    @property
    def duration(self) -> Optional[float]:
        return self._duration

    @property
    def suggestions(self) -> Optional[List[str]]:
        return self._suggestions


class CompilationTooLargeException(VideoException):
    def __init__(self, total_duration: float, suggestions: Optional[List[str]] = None) -> None:
        self._total_duration = total_duration
        self._suggestions = suggestions
        super().__init__(f"Compilation too large: {total_duration}s")

    @property
    def total_duration(self) -> float:
        return self._total_duration

    @property
    def suggestions(self) -> Optional[List[str]]:
        return self._suggestions
