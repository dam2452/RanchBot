from abc import ABC
import logging
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
)

from preprocessor.core.base_processor import (
    BaseProcessor,
    ProcessingItem,
)
from preprocessor.core.episode_manager import EpisodeManager


class BaseVideoProcessor(BaseProcessor, ABC): #Class BaseVideoProcessor must implement all abstract methods
    def __init__(
        self,
        args: Dict[str, Any],
        class_name: str,
        error_exit_code: int,
        input_videos_key: str = "videos",
    ):
        super().__init__(
            args=args,
            class_name=class_name,
            error_exit_code=error_exit_code,
            loglevel=logging.DEBUG,
        )

        self.input_videos: Path = Path(self._args[input_videos_key])
        episodes_json_path = self._args.get("episodes_info_json")
        self.episode_manager = EpisodeManager(episodes_json_path, self.series_name)

    def _get_processing_items(self) -> List[ProcessingItem]:
        return self._create_video_processing_items(
            source_path=self.input_videos,
            extensions=self.get_video_glob_patterns(),
            episode_manager=self.episode_manager,
            skip_unparseable=True,
        )
