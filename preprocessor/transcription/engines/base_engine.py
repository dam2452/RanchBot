from abc import (
    ABC,
    abstractmethod,
)
from pathlib import Path
from typing import Dict


class TranscriptionEngine(ABC):
    @abstractmethod
    def transcribe(self, audio_path: Path) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_name(self) -> str:
        pass
