import json
from pathlib import Path
from typing import (
    Any,
    Dict,
)

from preprocessor.utils.error_handling_logger import ErrorHandlingLogger


class SrtGenerator:
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

                srt_content = self._convert_to_srt_format(data)

                output_file = self.output_dir / json_file.name.replace(".json", ".srt")
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(srt_content)

                self.logger.info(f"Generated SRT: {output_file}")

            except Exception as e:
                self.logger.error(f"Failed to generate SRT for {json_file}: {e}")

    def _convert_to_srt_format(self, data: Dict[str, Any]) -> str:
        segments = data.get("segments", [])
        srt_lines = []
        index = 1

        for seg in segments:
            start = seg.get("start", 0.0)
            end = seg.get("end", 0.0)
            text = seg.get("text", "").strip()

            if not text:
                continue

            start_time = self._format_timestamp(start)
            end_time = self._format_timestamp(end)

            srt_lines.append(f"{index}")
            srt_lines.append(f"{start_time} --> {end_time}")
            srt_lines.append(text)
            srt_lines.append("")

            index += 1

        return "\n".join(srt_lines)

    def _format_timestamp(self, seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)

        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
