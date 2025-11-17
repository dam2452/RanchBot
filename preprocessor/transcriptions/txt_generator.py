from pathlib import Path
from typing import (
    Any,
    Dict,
)

from preprocessor.transcriptions.base_generator import BaseTranscriptionGenerator


class TxtGenerator(BaseTranscriptionGenerator):
    def _process_file(self, json_file: Path, data: Dict[str, Any]) -> None:
        pass

    def _get_output_filename(self, json_file: Path) -> str:
        return json_file.name.replace(".json", ".txt")

    def _convert_to_txt_format(self, data: Dict[str, Any]) -> str:
        segments = data.get("segments", [])

        text_parts = []
        for seg in segments:
            text = seg.get("text", "").strip()
            if text:
                text_parts.append(text)

        return " ".join(text_parts)
