from abc import (
    ABC,
    abstractmethod,
)
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
)

from rich.progress import Progress


class BaseKeyframeStrategy(ABC):
    @abstractmethod
    def extract_frame_requests(
        self,
        video_path: Path,
        data: Dict[str, Any],
        progress: Progress,
    ) -> List[Dict[str, Any]]:
        pass
