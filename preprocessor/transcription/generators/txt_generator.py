from pathlib import Path
from typing import (
    Any,
    Dict,
)

from preprocessor.core.constants import FILE_EXTENSIONS
from preprocessor.transcription.generators.base_generator import BaseTranscriptionGenerator


class TxtGenerator(BaseTranscriptionGenerator):
    def _process_file(self, json_file: Path, data: Dict[str, Any]) -> None:
        pass

    def _get_output_filename(self, json_file: Path) -> str:
        return json_file.name.replace(FILE_EXTENSIONS["json"], FILE_EXTENSIONS["txt"])

    @staticmethod
    def convert_to_txt_format(data: Dict[str, Any]) -> str:
        segments = data.get("segments", [])

        text_parts = []
        for seg in segments:
            text = seg.get("text", "").strip()
            if text:
                text_parts.append(text)

        return " ".join(text_parts)
