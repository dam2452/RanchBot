import json
from pathlib import Path
from typing import (
    Any,
    Dict,
    Literal,
)

from preprocessor.config.constants import (
    FILE_EXTENSIONS,
    FILE_SUFFIXES,
)
from preprocessor.services.transcription.generators.base_generator import BaseTranscriptionGenerator
from preprocessor.services.transcription.utils import TranscriptionUtils


class JsonGenerator(BaseTranscriptionGenerator):
    def __init__(self, format_type: Literal['full', 'simple', 'segmented'], *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.__format_type = format_type

    def convert(self, data: Dict[str, Any]) -> Dict[str, Any]:
        converters = {
            'full': self.convert_to_full_format,
            'simple': self.convert_to_simple_format,
            'segmented': self.convert_to_segmented_format,
        }
        if self.__format_type not in converters:
            raise ValueError(f'Unknown format type: {self.__format_type}')
        return converters[self.__format_type](data)

    @staticmethod
    def convert_to_full_format(data: Dict[str, Any]) -> Dict[str, Any]:
        segments = data.get('segments', [])
        full_text = ' '.join(seg.get('text', '').strip() for seg in segments)

        language = data.get('language', 'pol').lower()
        language_code = 'pol' if language in {'polish', 'pol'} else language

        words = []
        for seg in segments:
            words.extend(TranscriptionUtils.convert_words_list(seg.get('words', [])))

        return {
            'language_code': language_code,
            'language_probability': 1.0,
            'text': full_text,
            'words': words,
        }

    @staticmethod
    def convert_to_segmented_format(data: Dict[str, Any]) -> Dict[str, Any]:
        segments = data.get('segments', [])
        result = []
        for seg in segments:
            result.append({
                'text': seg.get('text', '').strip(),
                'words': TranscriptionUtils.convert_words_list(seg.get('words', [])),
            })
        return {'segments': result}

    @staticmethod
    def convert_to_simple_format(data: Dict[str, Any]) -> Dict[str, Any]:
        segments = data.get('segments', [])
        result = []
        for seg in segments:
            words = seg.get('words', [])
            speaker = words[0].get('speaker_id', 'speaker_unknown') if words else 'speaker_unknown'
            result.append({
                'speaker': speaker,
                'text': seg.get('text', '').strip(),
            })
        return {'segments': result}

    def _get_output_filename(self, json_file: Path) -> str:
        if self.__format_type == 'full':
            return json_file.name
        suffix = FILE_SUFFIXES[self.__format_type]
        return json_file.name.replace(FILE_EXTENSIONS['json'], f"{suffix}{FILE_EXTENSIONS['json']}")

    def _process_file(self, json_file: Path, data: Dict[str, Any]) -> None:
        converted_data = self.convert(data)
        output_path = self._output_dir / self._get_output_filename(json_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(converted_data, f, indent=2, ensure_ascii=False)
