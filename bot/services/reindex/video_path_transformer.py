import logging
from pathlib import Path
from typing import (
    Dict,
    Optional,
)


class VideoPathTransformer:
    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def transform_video_path(
        self,
        doc: Dict,
        mp4_path: Optional[Path],
    ) -> Dict:
        if 'video_path' not in doc:
            return doc

        if mp4_path is None:
            self.logger.warning(
                f"No MP4 path provided for document, keeping old: {doc.get('video_path')}",
            )
            return doc

        if not mp4_path.exists():
            self.logger.warning(
                f"MP4 file does not exist: {mp4_path}",
            )

        doc['video_path'] = str(mp4_path)

        return doc

    def validate_mp4_exists(self, path: str) -> bool:
        return Path(path).exists()
