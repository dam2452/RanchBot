from pathlib import Path
from typing import (
    Any,
    Dict,
)

from preprocessor.config.constants import FILE_EXTENSIONS
from preprocessor.services.transcription.generators.base_generator import BaseTranscriptionGenerator


class TxtGenerator(BaseTranscriptionGenerator):
    @staticmethod
    def convert_to_txt_format(data: Dict[str, Any]) -> str:
        segments = data.get('segments', [])
        return ' '.join(seg.get('text', '').strip() for seg in segments if seg.get('text'))

    def _get_output_filename(self, json_file: Path) -> str:
        return json_file.name.replace(FILE_EXTENSIONS['json'], FILE_EXTENSIONS['txt'])

    def _process_file(self, json_file: Path, data: Dict[str, Any]) -> None:
        content = self.convert_to_txt_format(data)
        output_path = self._output_dir / self._get_output_filename(json_file)
        output_path.write_text(content, encoding='utf-8')
