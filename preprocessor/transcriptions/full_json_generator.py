import json
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
)

from preprocessor.utils.error_handling_logger import ErrorHandlingLogger


class FullJsonGenerator:
    def __init__(
        self,
        input_dir: Path,
        output_dir: Path,
        logger: ErrorHandlingLogger,
    ):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.logger = logger

    def generate(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)

        for json_file in self.input_dir.rglob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                full_json = self._convert_to_full_format(data)

                output_file = self.output_dir / json_file.name
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(full_json, f, indent=2, ensure_ascii=False)

                self.logger.info(f"Generated full JSON: {output_file}")

            except Exception as e:
                self.logger.error(f"Failed to generate full JSON for {json_file}: {e}")

    def _convert_to_full_format(self, data: Dict[str, Any]) -> Dict[str, Any]:
        segments = data.get("segments", [])

        full_text = " ".join(seg.get("text", "").strip() for seg in segments)

        language_code = data.get("language", "pol")
        if language_code == "Polish" or language_code == "polish":
            language_code = "pol"

        words = []
        for seg in segments:
            seg_words = seg.get("words", [])
            for word in seg_words:
                words.append({
                    "text": word.get("word", word.get("text", "")).strip(),
                    "start": word.get("start", 0.0),
                    "end": word.get("end", 0.0),
                    "type": "word",
                    "speaker_id": "speaker_unknown",
                    "logprob": word.get("probability", 0.0),
                })

        return {
            "language_code": language_code,
            "language_probability": 1.0,
            "text": full_text,
            "words": words,
        }
