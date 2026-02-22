import json
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
)


class TranscriptionUtils:
    @staticmethod
    def convert_words_list(words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [
            {
                'word': word.get('text', word.get('word', '')),
                'start': word.get('start', 0.0),
                'end': word.get('end', 0.0),
                'probability': word.get('probability', word.get('confidence', 1.0)),
                'speaker_id': word.get('speaker_id', 'speaker_unknown'),
            }
            for word in words
        ]

    @staticmethod
    def fix_transcription_file_unicode(file_path: Path) -> bool:
        if not file_path.exists():
            return False

        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
            f.seek(0)
            data: Dict[str, Any] = json.load(f)

        new_content = json.dumps(data, ensure_ascii=False, indent=2)

        if original_content != new_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True
        return False


class WhisperUtils:
    LANGUAGE_MAP: Dict[str, str] = {
        'polish': 'pl',
        'english': 'en',
        'german': 'de',
        'french': 'fr',
        'spanish': 'es',
    }

    @staticmethod
    def get_language_code(language: str) -> str:
        return WhisperUtils.LANGUAGE_MAP.get(language.lower(), language.lower())

    @staticmethod
    def build_transcription_result(segments: Any, language: Optional[str] = None) -> Dict[str, Any]:
        result: Dict[str, Any] = {'text': '', 'segments': []}
        if language:
            result['language'] = language

        for segment in segments:
            segment_dict = WhisperUtils.__process_segment(segment)
            result['segments'].append(segment_dict)
            result['text'] += segment.text
        return result

    @staticmethod
    def __process_segment(segment: Any) -> Dict[str, Any]:
        words: List[Dict[str, Any]] = []
        if hasattr(segment, 'words') and segment.words:
            for word in segment.words:
                words.append({
                    'word': word.word,
                    'start': word.start,
                    'end': word.end,
                    'probability': word.probability,
                })

        return {
            'id': segment.id,
            'seek': 0,
            'start': segment.start,
            'end': segment.end,
            'text': segment.text,
            'tokens': [],
            'avg_logprob': segment.avg_logprob,
            'compression_ratio': segment.compression_ratio,
            'no_speech_prob': segment.no_speech_prob,
            'words': words,
        }
