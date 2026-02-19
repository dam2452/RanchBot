from abc import (
    ABC,
    abstractmethod,
)
from pathlib import Path
from typing import (
    Any,
    Dict,
)


class TranscriptionEngine(ABC):
    def cleanup(self) -> None:
        pass

    @abstractmethod
    def get_name(self) -> str:
        pass

    @abstractmethod
    def transcribe(self, audio_path: Path) -> Dict[str, Any]:
        pass
