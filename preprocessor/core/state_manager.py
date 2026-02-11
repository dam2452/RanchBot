from dataclasses import (
    asdict,
    dataclass,
    field,
)
from datetime import datetime
import json
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from preprocessor.lib.ui.console import console


@dataclass
class StepCheckpoint:
    step: str
    episode: str
    completed_at: str

@dataclass
class InProgressStep:
    step: str
    episode: str
    started_at: str
    temp_files: List[str] = field(default_factory=list)

@dataclass
class ProcessingState:
    series_name: str
    started_at: str
    last_checkpoint: str
    completed_steps: List[StepCheckpoint] = field(default_factory=list)
    in_progress: Optional[InProgressStep] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'series_name': self.series_name,
            'started_at': self.started_at,
            'last_checkpoint': self.last_checkpoint,
            'completed_steps': [asdict(step) for step in self.completed_steps],
            'in_progress': asdict(self.in_progress) if self.in_progress else None,
        }

    @classmethod
    def __from_dict(cls, data: Dict[str, Any]) -> 'ProcessingState':  # pylint: disable=unused-private-member
        completed_steps = [
            StepCheckpoint(**step) for step in data.get('completed_steps', [])
        ]
        in_progress_data = data.get('in_progress')
        in_progress = (
            InProgressStep(**in_progress_data) if in_progress_data else None
        )
        return cls(
            series_name=data['series_name'],
            started_at=data['started_at'],
            last_checkpoint=data['last_checkpoint'],
            completed_steps=completed_steps,
            in_progress=in_progress,
        )

class StateManager:
    STATE_FILE_TEMPLATE: str = '.preprocessing_state_{series}.json'

    def __init__(self, series_name: str, working_dir: Path = Path('.')) -> None:
        self.__series_name: str = series_name
        state_filename: str = self.STATE_FILE_TEMPLATE.format(series=series_name)
        self.__state_file: Path = working_dir / state_filename
        self.__state: Optional[ProcessingState] = None

    def load_or_create_state(self) -> ProcessingState:
        if self.__state_file.exists():
            console.print(f'[yellow]Found existing state file: {self.__state_file}[/yellow]')
            with open(self.__state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.__state = ProcessingState.__from_dict(data)
                console.print(f'[green]Loaded state for series: {self.__state.series_name}[/green]')
                console.print(f'[green]Completed steps: {len(self.__state.completed_steps)}[/green]')
                return self.__state
        else:
            console.print('[blue]Creating new processing state...[/blue]')
            now = datetime.now().isoformat()
            self.__state = ProcessingState(
                series_name=self.__series_name,
                started_at=now,
                last_checkpoint=now,
            )
            self.__save_state()
            return self.__state

    def __save_state(self) -> None:
        if self.__state is None:
            return
        self.__state.last_checkpoint = datetime.now().isoformat()
        with open(self.__state_file, 'w', encoding='utf-8') as f:
            json.dump(self.__state.to_dict(), f, indent=2, ensure_ascii=False)

    def mark_step_started(
        self, step: str, episode: str, temp_files: Optional[List[str]] = None,
    ) -> None:
        if self.__state is None:
            raise RuntimeError('State not initialized')
        self.__state.in_progress = InProgressStep(
            step=step,
            episode=episode,
            started_at=datetime.now().isoformat(),
            temp_files=temp_files or [],
        )
        self.__save_state()
        console.print(f'[cyan]Started: {step} for {episode}[/cyan]')

    def mark_step_completed(self, step: str, episode: str) -> None:
        if self.__state is None:
            raise RuntimeError('State not initialized')
        checkpoint = StepCheckpoint(
            step=step,
            episode=episode,
            completed_at=datetime.now().isoformat(),
        )
        self.__state.completed_steps.append(checkpoint)
        self.__state.in_progress = None
        self.__save_state()
        console.print(f'[green]✓ Completed: {step} for {episode}[/green]')

    def is_step_completed(self, step: str, episode: str) -> bool:
        if self.__state is None:
            return False
        return any(
            (s.step == step and s.episode == episode)
            for s in self.__state.completed_steps
        )

    def __rollback_in_progress(self) -> None: # pylint: disable=unused-private-member
        if self.__state is None or self.__state.in_progress is None:
            return
        console.print(
            f'[yellow]Rolling back in-progress step: '
            f'{self.__state.in_progress.step}[/yellow]',
        )
        for temp_file in self.__state.in_progress.temp_files:
            temp_path = Path(temp_file)
            if temp_path.exists():
                try:
                    temp_path.unlink()
                    console.print(f'[yellow]Removed temp file: {temp_file}[/yellow]')
                except OSError as e:
                    console.print(f'[red]Failed to remove {temp_file}: {e}[/red]')
        self.__state.in_progress = None
        self.__save_state()

    def cleanup(self) -> None:
        if self.__state_file.exists():
            console.print(f'[blue]Cleaning up state file: {self.__state_file}[/blue]')
            self.__state_file.unlink()
