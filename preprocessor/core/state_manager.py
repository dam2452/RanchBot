from dataclasses import (
    asdict,
    dataclass,
    field,
)
from datetime import datetime
import json
from pathlib import Path
import threading
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from preprocessor.services.ui.console import console


@dataclass(frozen=True)
class StepCheckpoint:
    completed_at: str
    episode: str
    step: str


@dataclass(frozen=True)
class InProgressStep:
    episode: str
    started_at: str
    step: str
    temp_files: List[str] = field(default_factory=list)


@dataclass
class ProcessingState:
    last_checkpoint: str
    series_name: str
    started_at: str
    completed_steps: List[StepCheckpoint] = field(default_factory=list)
    in_progress: List[InProgressStep] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'series_name': self.series_name,
            'started_at': self.started_at,
            'last_checkpoint': self.last_checkpoint,
            'completed_steps': [asdict(step) for step in self.completed_steps],
            'in_progress': [asdict(step) for step in self.in_progress],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProcessingState':
        completed_steps = [
            StepCheckpoint(**step) for step in data.get('completed_steps', [])
        ]
        in_progress_data = data.get('in_progress', [])
        in_progress = (
            [InProgressStep(**step) for step in in_progress_data]
            if isinstance(in_progress_data, list)
            else []
        )

        return cls(
            series_name=data['series_name'],
            started_at=data['started_at'],
            last_checkpoint=data['last_checkpoint'],
            completed_steps=completed_steps,
            in_progress=in_progress,
        )


class StateManager:
    __STATE_FILE_TEMPLATE: str = '.preprocessing_state_{series}.json'
    __lock = threading.Lock()

    def __init__(self, series_name: str, working_dir: Path = Path('.')) -> None:
        self.__series_name = series_name

        state_filename = self.__STATE_FILE_TEMPLATE.format(series=series_name)
        self.__state_file: Path = working_dir / state_filename
        self.__state: Optional[ProcessingState] = None

    def cleanup(self) -> None:
        with self.__lock:
            if self.__state_file.exists():
                console.print(f'[blue]Cleaning up state file: {self.__state_file}[/blue]')
                self.__state_file.unlink()

    def is_step_completed(self, step: str, episode: str) -> bool:
        if self.__state is None:
            return False

        return any(
            s.step == step and s.episode == episode
            for s in self.__state.completed_steps
        )

    def load_or_create_state(self) -> ProcessingState:
        if self.__state_file.exists():
            return self.__load_existing_state()
        return self.__create_new_state()

    def mark_step_completed(self, step: str, episode: str) -> None:
        with self.__lock:
            self.__ensure_state_initialized()

            checkpoint = StepCheckpoint(
                step=step,
                episode=episode,
                completed_at=datetime.now().isoformat(),
            )

            self.__state.completed_steps.append(checkpoint)
            self.__state.in_progress = [
                s for s in self.__state.in_progress
                if not (s.step == step and s.episode == episode)
            ]
            self.__save_state()

            console.print(f'[green]Completed: {step} for {episode}[/green]')

    def mark_step_started(
            self, step: str, episode: str, temp_files: Optional[List[str]] = None,
    ) -> None:
        with self.__lock:
            self.__ensure_state_initialized()

            in_progress_step = InProgressStep(
                step=step,
                episode=episode,
                started_at=datetime.now().isoformat(),
                temp_files=temp_files or [],
            )
            self.__state.in_progress.append(in_progress_step)
            self.__save_state()

            console.print(f'[cyan]Started: {step} for {episode}[/cyan]')

    def __load_existing_state(self) -> ProcessingState:
        console.print(f'[yellow]Found existing state file: {self.__state_file}[/yellow]')

        with open(self.__state_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.__state = ProcessingState.from_dict(data)

        console.print(f'[green]Loaded state for series: {self.__state.series_name}[/green]')
        console.print(f'[green]Completed steps: {len(self.__state.completed_steps)}[/green]')
        return self.__state

    def __create_new_state(self) -> ProcessingState:
        console.print('[blue]Creating new processing state...[/blue]')
        now = datetime.now().isoformat()

        self.__state = ProcessingState(
            series_name=self.__series_name,
            started_at=now,
            last_checkpoint=now,
        )
        self.__save_state()
        return self.__state

    def __ensure_state_initialized(self) -> None:
        if self.__state is None:
            raise RuntimeError('State not initialized. Call load_or_create_state() first.')

    def __save_state(self) -> None:
        if self.__state is None:
            return

        self.__state.last_checkpoint = datetime.now().isoformat()
        with open(self.__state_file, 'w', encoding='utf-8') as f:
            json.dump(self.__state.to_dict(), f, indent=2, ensure_ascii=False)
