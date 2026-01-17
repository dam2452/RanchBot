from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
)

from preprocessor.config.config import settings
from preprocessor.core.base_processor import (
    BaseProcessor,
    OutputSpec,
    ProcessingItem,
)
from preprocessor.core.episode_manager import EpisodeManager
from preprocessor.utils.transcription_utils import fix_transcription_file_unicode


class TranscriptionUnicodeFixer(BaseProcessor):
    def __init__(self, args: Dict[str, Any]) -> None:
        super().__init__(
            args=args,
            class_name=self.__class__.__name__,
            error_exit_code=2,
            loglevel=args.get("loglevel", 20),
        )

        self.transcription_jsons = Path(self._args.get("transcription_jsons", settings.transcription.output_dir))
        episodes_info_json = self._args.get("episodes_info_json")
        self.episode_manager = EpisodeManager(episodes_info_json, self.series_name)

    def _validate_args(self, args: Dict[str, Any]) -> None:
        pass

    def _get_processing_items(self) -> List[ProcessingItem]:
        transcription_files = list(self.transcription_jsons.rglob("*.json"))

        return [
            ProcessingItem(
                episode_id=f"unicode_fix_{i}",
                input_path=trans_file,
                metadata={"file": trans_file},
            )
            for i, trans_file in enumerate(transcription_files)
        ]

    def _get_expected_outputs(self, item: ProcessingItem) -> List[OutputSpec]:
        return [OutputSpec(path=item.input_path, required=True)]

    def _process_item(self, item: ProcessingItem, missing_outputs: List[OutputSpec]) -> None:
        trans_file = item.metadata["file"]

        try:
            was_fixed = fix_transcription_file_unicode(trans_file)
            if was_fixed:
                self.logger.info(f"Fixed unicode escapes in: {trans_file.name}")
            else:
                self.logger.debug(f"No unicode escapes found in: {trans_file.name}")
        except Exception as e:
            self.logger.error(f"Error fixing unicode in {trans_file.name}: {e}")
