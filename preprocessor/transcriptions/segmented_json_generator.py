import json
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
)

from preprocessor.utils.error_handling_logger import ErrorHandlingLogger


class SegmentedJsonGenerator:
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

                segmented_json = self._convert_to_segmented_format(data)

                output_file = self.output_dir / json_file.name.replace(".json", "_segmented.json")
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(segmented_json, f, indent=2, ensure_ascii=False)

                self.logger.info(f"Generated segmented JSON: {output_file}")

            except Exception as e:
                self.logger.error(f"Failed to generate segmented JSON for {json_file}: {e}")

    def _convert_to_segmented_format(self, data: Dict[str, Any]) -> Dict[str, Any]:
        segments = data.get("segments", [])
        result_segments = []

        for seg in segments:
            text = seg.get("text", "").strip()
            seg_words = seg.get("words", [])

            words = []
            for word in seg_words:
                words.append({
                    "text": word.get("word", word.get("text", "")).strip(),
                    "start": word.get("start", 0.0),
                    "end": word.get("end", 0.0),
                    "type": "word",
                    "speaker_id": "speaker_unknown",
                    "logprob": word.get("probability", 0.0),
                })

            result_segments.append({
                "text": text,
                "words": words,
            })

        return {"segments": result_segments}
