import logging
from pathlib import Path
from typing import (
    Any,
    Dict,
    Optional,
)


class VideoPathTransformer:
    def __init__(self, logger: logging.Logger):
        self.__logger = logger

    def transform_video_path(
        self,
        doc: Dict[str, Any],
        mp4_path: Optional[Path],
    ) -> Dict[str, Any]:
        if 'video_path' not in doc:
            return doc

        if mp4_path is None:
            self.__logger.warning(
                f"No MP4 path provided for document, keeping old: {doc.get('video_path')}",
            )
            return doc

        if not mp4_path.exists():
            self.__logger.warning(
                f"MP4 file does not exist: {mp4_path}",
            )

        doc['video_path'] = str(mp4_path)

        return doc
