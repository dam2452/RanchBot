import json
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
)

from preprocessor.utils.error_handling_logger import ErrorHandlingLogger


class SimpleJsonGenerator:
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

                simple_json = self._convert_to_simple_format(data)

                output_file = self.output_dir / json_file.name.replace(".json", "_simple.json")
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(simple_json, f, indent=2, ensure_ascii=False)

                self.logger.info(f"Generated simple JSON: {output_file}")

            except Exception as e:
                self.logger.error(f"Failed to generate simple JSON for {json_file}: {e}")

    def _convert_to_simple_format(self, data: Dict[str, Any]) -> Dict[str, Any]:
        segments = data.get("segments", [])
        result_segments = []

        for seg in segments:
            text = seg.get("text", "").strip()

            result_segments.append({
                "speaker": "speaker_unknown",
                "text": text,
            })

        return {"segments": result_segments}
