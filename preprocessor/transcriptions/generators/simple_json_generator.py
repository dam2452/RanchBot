from pathlib import Path
from typing import (
    Any,
    Dict,
)

from preprocessor.transcriptions.generators.base_generator import BaseTranscriptionGenerator


class SimpleJsonGenerator(BaseTranscriptionGenerator):
    def _process_file(self, json_file: Path, data: Dict[str, Any]) -> None:
        pass

    def _get_output_filename(self, json_file: Path) -> str:
        return json_file.name.replace(".json", "_simple.json")

    @staticmethod
    def convert_to_simple_format(data: Dict[str, Any]) -> Dict[str, Any]:
        segments = data.get("segments", [])
        result_segments = []

        for seg in segments:
            text = seg.get("text", "").strip()
            seg_words = seg.get("words", [])

            speaker = "speaker_unknown"
            if seg_words:
                speaker = seg_words[0].get("speaker_id", "speaker_unknown")

            result_segments.append({
                "speaker": speaker,
                "text": text,
            })

        return {"segments": result_segments}
