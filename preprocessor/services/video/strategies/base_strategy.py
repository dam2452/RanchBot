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

from preprocessor.config.types import FrameRequest


class BaseKeyframeStrategy(ABC):
    @abstractmethod
    def extract_frame_requests(
        self, video_path: Path, data: Dict[str, Any],
    ) -> List[FrameRequest]:
        pass
