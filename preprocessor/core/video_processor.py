from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from preprocessor.core.base_processor import (
    BaseProcessor,
    ProcessingItem,
)
from preprocessor.episodes import EpisodeManager


class VideoProcessor(BaseProcessor):
    def __init__(
        self,
        args: Dict[str, Any],
        class_name: str,
        error_exit_code: int,
        loglevel: int,
    ):
        super().__init__(
            args=args,
            class_name=class_name,
            error_exit_code=error_exit_code,
            loglevel=loglevel,
        )

        self.input_videos: Path = Path(self._args["videos"])
        self.subdirectory_filter: Optional[str] = None
        episodes_json_path = self._args.get("episodes_info_json")
        self.episode_manager = EpisodeManager(episodes_json_path, self.series_name)

    def _get_processing_items(self) -> List[ProcessingItem]:
        return self._create_video_processing_items(
            source_path=self.input_videos,
            extensions=self.get_video_glob_patterns(),
            episode_manager=self.episode_manager,
            skip_unparseable=True,
            subdirectory_filter=self.subdirectory_filter,
        )

    def _validate_videos_required(self, args: Dict[str, Any]) -> None:
        if "videos" not in args:
            raise ValueError("videos path is required")
