from dataclasses import (
    dataclass,
    field,
)
from datetime import datetime
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
)


@dataclass
class StepMetadata:
    name: str
    step_num: str
    duration_seconds: Optional[float] = None
    end_time: Optional[datetime] = None
    exit_code: Optional[int] = None
    extra_info: Dict[str, Any] = field(default_factory=dict)
    start_time: Optional[datetime] = None
    status: str = 'pending'

    def skip(self) -> None:
        self.status = 'skipped'

    def start(self) -> None:
        self.start_time = datetime.now()
        self.status = 'running'

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'step_num': self.step_num,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': (
                round(self.duration_seconds, 2) if self.duration_seconds else None
            ),
            'status': self.status,
            'exit_code': self.exit_code,
            'extra_info': self.extra_info,
        }


class ProcessingMetadata:
    def __init__(self, series_name: str, params: Dict[str, Any]) -> None:
        self.__series_name = series_name
        self.__params = self.__sanitize_params(params)
        self.__start_time = datetime.now()
        self.__end_time: Optional[datetime] = None
        self.__total_duration_seconds: Optional[float] = None
        self.__steps: List[StepMetadata] = []
        self.__final_status = 'running'

    @property
    def final_status(self) -> str:
        return self.__final_status

    @final_status.setter
    def final_status(self, value: str) -> None:
        self.__final_status = value

    @property
    def end_time(self) -> Optional[datetime]:
        return self.__end_time

    @end_time.setter
    def end_time(self, value: datetime) -> None:
        self.__end_time = value

    @property
    def total_duration_seconds(self) -> Optional[float]:
        return self.__total_duration_seconds

    @total_duration_seconds.setter
    def total_duration_seconds(self, value: float) -> None:
        self.__total_duration_seconds = value

    def add_step(self, name: str, step_num: str) -> StepMetadata:
        step = StepMetadata(name=name, step_num=step_num)
        self.__steps.append(step)
        return step

    def to_dict(self) -> Dict[str, Any]:
        return {
            'series_name': self.__series_name,
            'start_time': self.__start_time.isoformat(),
            'end_time': self.__end_time.isoformat() if self.__end_time else None,
            'final_status': self.__final_status,
            'parameters': self.__params,
            'steps': [step.to_dict() for step in self.__steps],
            'statistics': self.__get_statistics(),
        }

    def __get_statistics(self) -> Dict[str, Any]:
        completed_steps = [s for s in self.__steps if s.status == 'success']
        failed_steps = [s for s in self.__steps if s.status == 'failed']
        skipped_steps = [s for s in self.__steps if s.status == 'skipped']

        step_durations = [
            s.duration_seconds for s in self.__steps if s.duration_seconds is not None
        ]

        avg_duration = (
            round(sum(step_durations) / len(step_durations), 2)
            if step_durations else None
        )

        return {
            'total_steps': len(self.__steps),
            'completed_steps': len(completed_steps),
            'failed_steps': len(failed_steps),
            'skipped_steps': len(skipped_steps),
            'total_duration_seconds': (
                round(self.__total_duration_seconds, 2)
                if self.__total_duration_seconds else None
            ),
            'average_step_duration_seconds': avg_duration,
        }

    @staticmethod
    def __sanitize_params(params: Dict[str, Any]) -> Dict[str, Any]:
        sanitized: Dict[str, Any] = {}
        ignored_keys = {'state_manager'}

        for key, value in params.items():
            if key in ignored_keys:
                continue

            if isinstance(value, Path):
                sanitized[key] = str(value)
            elif isinstance(value, (str, int, float, bool, list, dict, type(None))):
                sanitized[key] = value
            else:
                sanitized[key] = str(value)

        return sanitized
