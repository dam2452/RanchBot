import codecs
import json
from pathlib import Path
import re
from typing import (
    Any,
    Dict,
    List,
)


def _convert_word_to_standard_format(word: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "text": word.get("word", word.get("text", "")).strip(),
        "start": word.get("start", 0.0),
        "end": word.get("end", 0.0),
        "type": "word",
        "speaker_id": word.get("speaker_id", "speaker_unknown"),
        "logprob": word.get("probability", 0.0),
    }


def convert_words_list(seg_words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [_convert_word_to_standard_format(word) for word in seg_words]


def _fix_unicode_escapes(text: str) -> str:
    def replace_unicode(match):
        unicode_str = match.group(0)
        try:
            return codecs.decode(unicode_str, 'unicode_escape')
        except Exception:
            return unicode_str

    pattern = r'\\u[0-9a-fA-F]{4}'
    return re.sub(pattern, replace_unicode, text)


def fix_transcription_file_unicode(file_path: Path) -> bool:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        if '\\u' not in content:
            return False

        fixed_content = _fix_unicode_escapes(content)

        if fixed_content != content:
            data = json.loads(fixed_content)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True

        return False
    except Exception:
        return False
