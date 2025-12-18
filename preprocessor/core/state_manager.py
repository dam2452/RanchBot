from dataclasses import (
    asdict,
    dataclass,
    field,
)
from datetime import datetime
import json
from pathlib import Path
import signal
import sys
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)

console = Console()


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
            "series_name": self.series_name,
            "started_at": self.started_at,
            "last_checkpoint": self.last_checkpoint,
            "completed_steps": [asdict(step) for step in self.completed_steps],
            "in_progress": asdict(self.in_progress) if self.in_progress else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProcessingState":
        completed_steps = [
            StepCheckpoint(**step) for step in data.get("completed_steps", [])
        ]
        in_progress_data = data.get("in_progress")
        in_progress = InProgressStep(**in_progress_data) if in_progress_data else None

        return cls(
            series_name=data["series_name"],
            started_at=data["started_at"],
            last_checkpoint=data["last_checkpoint"],
            completed_steps=completed_steps,
            in_progress=in_progress,
        )


class StateManager:
    STATE_FILE: str = ".preprocessing_state.json"

    def __init__(self, series_name: str, working_dir: Path = Path(".")) -> None:
        self.__series_name: str = series_name
        self.__working_dir: Path = working_dir
        self.__state_file: Path = working_dir / self.STATE_FILE
        self.__state: Optional[ProcessingState] = None
        self.__cleanup_registered: bool = False
        self.__interrupted: bool = False

    def load_or_create_state(self) -> ProcessingState:
        if self.__state_file.exists():
            console.print(f"[yellow]Found existing state file: {self.__state_file}[/yellow]")
            with open(self.__state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.__state = ProcessingState.from_dict(data)
                console.print(f"[green]Loaded state for series: {self.__state.series_name}[/green]")
                console.print(f"[green]Completed steps: {len(self.__state.completed_steps)}[/green]")
                return self.__state
        else:
            console.print("[blue]Creating new processing state...[/blue]")
            now = datetime.now().isoformat()
            self.__state = ProcessingState(
                series_name=self.__series_name,
                started_at=now,
                last_checkpoint=now,
            )
            self.save_state()
            return self.__state

    def save_state(self) -> None:
        if self.__state is None:
            return

        self.__state.last_checkpoint = datetime.now().isoformat()
        with open(self.__state_file, "w", encoding="utf-8") as f:
            json.dump(self.__state.to_dict(), f, indent=2, ensure_ascii=False)

    def mark_step_started(self, step: str, episode: str, temp_files: Optional[List[str]] = None) -> None:
        if self.__state is None:
            raise RuntimeError("State not initialized")

        self.__state.in_progress = InProgressStep(
            step=step,
            episode=episode,
            started_at=datetime.now().isoformat(),
            temp_files=temp_files or [],
        )
        self.save_state()
        console.print(f"[cyan]Started: {step} for {episode}[/cyan]")

    def mark_step_completed(self, step: str, episode: str) -> None:
        if self.__state is None:
            raise RuntimeError("State not initialized")

        checkpoint = StepCheckpoint(
            step=step,
            episode=episode,
            completed_at=datetime.now().isoformat(),
        )
        self.__state.completed_steps.append(checkpoint)
        self.__state.in_progress = None
        self.save_state()
        console.print(f"[green]✓ Completed: {step} for {episode}[/green]")

    def is_step_completed(self, step: str, episode: str) -> bool:
        if self.__state is None:
            return False

        return any(
            s.step == step and s.episode == episode
            for s in self.__state.completed_steps
        )

    def rollback_in_progress(self) -> None:
        if self.__state is None or self.__state.in_progress is None:
            return

        console.print(f"[yellow]Rolling back in-progress step: {self.__state.in_progress.step}[/yellow]")

        for temp_file in self.__state.in_progress.temp_files:
            temp_path = Path(temp_file)
            if temp_path.exists():
                try:
                    temp_path.unlink()
                    console.print(f"[yellow]Removed temp file: {temp_file}[/yellow]")
                except Exception as e:
                    console.print(f"[red]Failed to remove {temp_file}: {e}[/red]")

        self.__state.in_progress = None
        self.save_state()

    def cleanup(self) -> None:
        if self.__state_file.exists():
            console.print(f"[blue]Cleaning up state file: {self.__state_file}[/blue]")
            self.__state_file.unlink()

    def register_interrupt_handler(self) -> None:
        if self.__cleanup_registered:
            return

        def signal_handler(_sig: int, _frame: Any) -> None:
            if self.__interrupted:
                console.print("\n[red]Force quit! Not cleaning up.[/red]")
                sys.exit(1)

            self.__interrupted = True
            console.print("\n[yellow]Interrupt received (Ctrl+C)...[/yellow]")
            console.print("[yellow]Rolling back incomplete work...[/yellow]")
            self.rollback_in_progress()
            console.print("[green]Cleanup complete. You can resume later.[/green]")
            console.print("[blue]To resume: run the same command again[/blue]")
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        self.__cleanup_registered = True
        console.print("[blue]Interrupt handler registered (Ctrl+C to safely stop)[/blue]")

    def get_resume_info(self) -> Optional[str]:
        if self.__state is None or not self.__state.completed_steps:
            return None

        last_step = self.__state.completed_steps[-1]
        return f"Resuming from: {last_step.step} ({last_step.episode}) at {last_step.completed_at}"

    @staticmethod
    def create_progress_bar(_total_episodes: int, _description: str = "Processing") -> Progress:
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console,
        )
        return progress
