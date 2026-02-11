from pathlib import Path
from typing import List


class VideoDiscovery:
    DEFAULT_EXTENSIONS: List[str] = ["*.mp4", "*.mkv", "*.avi"]

    @staticmethod
    def discover(
        source_path: Path,
        extensions: List[str] = None,
    ) -> List[Path]:
        if extensions is None:
            extensions = VideoDiscovery.DEFAULT_EXTENSIONS

        videos = []
        for ext in extensions:
            videos.extend(source_path.glob(f"**/{ext}"))
        return sorted(videos)
