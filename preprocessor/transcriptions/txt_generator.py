import json
from pathlib import Path
from typing import (
    Any,
    Dict,
)

from preprocessor.utils.error_handling_logger import ErrorHandlingLogger


class TxtGenerator:
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

                txt_content = self._convert_to_txt_format(data)

                output_file = self.output_dir / json_file.name.replace(".json", ".txt")
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(txt_content)

                self.logger.info(f"Generated TXT: {output_file}")

            except Exception as e:
                self.logger.error(f"Failed to generate TXT for {json_file}: {e}")

    def _convert_to_txt_format(self, data: Dict[str, Any]) -> str:
        segments = data.get("segments", [])

        text_parts = []
        for seg in segments:
            text = seg.get("text", "").strip()
            if text:
                text_parts.append(text)

        return " ".join(text_parts)
