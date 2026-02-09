from pathlib import Path
from typing import (
    Any,
    Dict,
    Literal,
)

from preprocessor.core.constants import (
    FILE_EXTENSIONS,
    FILE_SUFFIXES,
)
from preprocessor.transcription.generators.base_generator import BaseTranscriptionGenerator
from preprocessor.utils.transcription_utils import convert_words_list


class JsonGenerator(BaseTranscriptionGenerator):
    def __init__(self, format_type: Literal["full", "simple", "segmented"], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.format_type = format_type

    def _process_file(self, json_file: Path, data: Dict[str, Any]) -> None:
        pass

    def _get_output_filename(self, json_file: Path) -> str:
        if self.format_type == "full":
            return json_file.name
        suffix = FILE_SUFFIXES[self.format_type]
        return json_file.name.replace(FILE_EXTENSIONS["json"], f"{suffix}{FILE_EXTENSIONS['json']}")

    def convert(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if self.format_type == "full":
            return self.convert_to_full_format(data)
        if self.format_type == "simple":
            return self.convert_to_simple_format(data)
        if self.format_type == "segmented":
            return self.convert_to_segmented_format(data)
        raise ValueError(f"Unknown format type: {self.format_type}")

    @staticmethod
    def convert_to_full_format(data: Dict[str, Any]) -> Dict[str, Any]:
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
