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

    @abstractmethod
    def transcribe(self, audio_path: Path) -> Dict[str, Any]:
        ...

    @abstractmethod
    def get_name(self) -> str:
        ...
