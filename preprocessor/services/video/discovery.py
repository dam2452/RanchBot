from pathlib import Path
from typing import (
    List,
    Optional,
)


class VideoDiscovery:
    DEFAULT_EXTENSIONS: List[str] = ["*.mp4", "*.mkv", "*.avi"]

    @staticmethod
    def discover(
            source_path: Path,
            extensions: Optional[List[str]] = None,
    ) -> List[Path]:
        if extensions is None:
            extensions = VideoDiscovery.DEFAULT_EXTENSIONS

        videos: List[Path] = []
        for ext in extensions:
            videos.extend(source_path.glob(f"**/{ext}"))

        return sorted(videos)
