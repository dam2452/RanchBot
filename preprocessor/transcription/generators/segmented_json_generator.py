from pathlib import Path
from typing import (
    Any,
    Dict,
)

from preprocessor.core.constants import (
    FILE_EXTENSIONS,
    FILE_SUFFIXES,
)
from preprocessor.transcription.generators.base_generator import BaseTranscriptionGenerator
from preprocessor.utils.transcription_utils import convert_words_list


class SegmentedJsonGenerator(BaseTranscriptionGenerator):
    def _process_file(self, json_file: Path, data: Dict[str, Any]) -> None:
        pass

    def _get_output_filename(self, json_file: Path) -> str:
        return json_file.name.replace(FILE_EXTENSIONS["json"], f"{FILE_SUFFIXES['segmented']}{FILE_EXTENSIONS['json']}")

    @staticmethod
    def convert_to_segmented_format(data: Dict[str, Any]) -> Dict[str, Any]:
        segments = data.get("segments", [])
        result_segments = []

        for seg in segments:
            text = seg.get("text", "").strip()
            seg_words = seg.get("words", [])

            result_segments.append({
                "text": text,
                "words": convert_words_list(seg_words),
            })

        return {"segments": result_segments}
