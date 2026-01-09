from pathlib import Path
from typing import Optional

from preprocessor.core.state_manager import StateManager
from preprocessor.utils.console import console


def create_state_manager(name: str, no_state: bool) -> Optional[StateManager]:
    if no_state or not name:
        return None

    state_manager = StateManager(series_name=name, working_dir=Path("."))
    state_manager.register_interrupt_handler()
    state_manager.load_or_create_state()

    resume_info = state_manager.get_resume_info()
    if resume_info:
        console.print(f"[cyan]{resume_info}[/cyan]")

    return state_manager
