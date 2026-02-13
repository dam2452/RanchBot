from pathlib import Path
from typing import (
    Any,
    Dict,
)

from preprocessor.config.constants import FILE_EXTENSIONS
from preprocessor.services.transcription.generators.base_generator import BaseTranscriptionGenerator


class SrtGenerator(BaseTranscriptionGenerator):
    def convert_to_srt_format(self, data: Dict[str, Any]) -> str:
        segments = data.get('segments', [])
        srt_lines = []
        index = 1

        for seg in segments:
            text = seg.get('text', '').strip()
            if not text:
                continue

            start_time = self.__format_timestamp(seg.get('start', 0.0))
            end_time = self.__format_timestamp(seg.get('end', 0.0))

            srt_lines.extend([str(index), f'{start_time} --> {end_time}', text, ''])
            index += 1

        return '\n'.join(srt_lines)

    def _get_output_filename(self, json_file: Path) -> str:
        return json_file.name.replace(FILE_EXTENSIONS['json'], FILE_EXTENSIONS['srt'])

    def _process_file(self, json_file: Path, data: Dict[str, Any]) -> None:
        content = self.convert_to_srt_format(data)
        output_path = self._output_dir / self._get_output_filename(json_file)
        output_path.write_text(content, encoding='utf-8')

    @staticmethod
    def __format_timestamp(seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int(seconds % 3600 // 60)
        secs = int(seconds % 60)
        millis = int(seconds % 1 * 1000)
        return f'{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}'
