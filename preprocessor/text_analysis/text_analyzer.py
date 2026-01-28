from datetime import datetime
import logging
from typing import (
    Any,
    Dict,
    List,
)

from preprocessor.config.config import (
    BASE_OUTPUT_DIR,
    settings,
)
from preprocessor.core.base_processor import (
    BaseProcessor,
    OutputSpec,
    ProcessingItem,
)
from preprocessor.core.episode_manager import EpisodeManager
from preprocessor.text_analysis.text_statistics import TextStatistics
from preprocessor.utils.file_utils import atomic_write_json


class TextAnalyzer(BaseProcessor):
    def __init__(self, args: Dict[str, Any]):
        super().__init__(
            args=args,
            class_name=self.__class__.__name__,
            error_exit_code=40,
            loglevel=logging.INFO,
        )
        self.transcriptions_base = BASE_OUTPUT_DIR / settings.output_subdirs.transcriptions
        self.language = args.get("language", "pl")
        self.episode_manager = EpisodeManager(
            args.get("episodes_info_json"),
            args.get("series_name", "ranczo"),
        )

    def _validate_args(self, args: Dict[str, Any]) -> None:
        if "series_name" not in args:
            raise ValueError("series_name is required")

    def _get_processing_items(self) -> List[ProcessingItem]:
        items = []

        if not self.transcriptions_base.exists():
            self.logger.error(f"Transcriptions directory not found: {self.transcriptions_base}")
            return items

        for season_dir in sorted(self.transcriptions_base.glob("S*")):
            if not season_dir.is_dir():
                continue

            for episode_dir in sorted(season_dir.glob("E*")):
                if not episode_dir.is_dir():
                    continue

                clean_subdir = episode_dir / settings.output_subdirs.transcription_subdirs.clean
                clean_txt_files = list(clean_subdir.glob("*_clean_transcription.txt"))
                if not clean_txt_files:
                    continue
                txt_file = clean_txt_files[0]

                episode_info = self.episode_manager.parse_filename(txt_file)
                if not episode_info:
                    self.logger.error(f"Cannot parse episode info from {txt_file.name}")
                    continue

                episode_id = EpisodeManager.get_episode_id_for_state(episode_info)

                items.append(
                    ProcessingItem(
                        episode_id=episode_id,
                        input_path=txt_file,
                        metadata={
                            "episode_info": episode_info,
                            "episode_dir": episode_dir,
                        },
                    ),
                )

        return items

    def _get_expected_outputs(self, item: ProcessingItem) -> List[OutputSpec]:
        episode_dir = item.metadata["episode_dir"]
        episode_info = item.metadata["episode_info"]
        clean_dir = episode_dir / settings.output_subdirs.transcription_subdirs.clean

        output_filename = self.episode_manager.file_naming.build_filename(
            episode_info,
            extension="json",
            suffix="text_stats",
        )
        output_file = clean_dir / output_filename

        return [OutputSpec(path=output_file, required=True)]

    def _process_item(self, item: ProcessingItem, missing_outputs: List[OutputSpec]) -> None:
        txt_file = item.input_path
        episode_dir = item.metadata["episode_dir"]
        episode_info = item.metadata["episode_info"]
        clean_dir = episode_dir / settings.output_subdirs.transcription_subdirs.clean

        output_filename = self.episode_manager.file_naming.build_filename(
            episode_info,
            extension="json",
            suffix="text_stats",
        )
        output_file = clean_dir / output_filename

        try:
            stats = TextStatistics.from_file(txt_file, language=self.language)

            result = {
                "metadata": {
                    "episode_id": episode_info.episode_code(),
                    "language": self.language,
                    "source_file": txt_file.name,
                    "analyzed_at": datetime.now().isoformat(),
                },
                **stats.to_dict(),
            }

            atomic_write_json(output_file, result)

            self.logger.info(
                f"Text analysis completed for {item.episode_id}: "
                f"{stats.words} words, {stats.sentences} sentences",
            )

        except Exception as e:
            self.logger.error(f"Failed to analyze {txt_file.name}: {e}")
            raise

    def _get_progress_description(self) -> str:
        return f"Analyzing transcription texts ({self.language})"
