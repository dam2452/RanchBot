from pathlib import Path
from typing import (
    Any,
    Dict,
)

from preprocessor.transcriptions.base_generator import BaseTranscriptionGenerator
from preprocessor.utils.transcription_utils import convert_words_list


class FullJsonGenerator(BaseTranscriptionGenerator):
    def _process_file(self, json_file: Path, data: Dict[str, Any]) -> None:
        pass

    def _get_output_filename(self, json_file: Path) -> str:
        return json_file.name

    def _convert_to_full_format(self, data: Dict[str, Any]) -> Dict[str, Any]:
        segments = data.get("segments", [])

        full_text = " ".join(seg.get("text", "").strip() for seg in segments)

        language_code = data.get("language", "pol")
        if language_code in {"Polish", "polish"}:
            language_code = "pol"

        words = []
        for seg in segments:
            seg_words = seg.get("words", [])
            words.extend(convert_words_list(seg_words))

        return {
            "language_code": language_code,
            "language_probability": 1.0,
            "text": full_text,
            "words": words,
        }
