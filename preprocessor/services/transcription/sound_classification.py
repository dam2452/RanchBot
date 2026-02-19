import re
from typing import (
    Any,
    Dict,
)

from preprocessor.config.types import (
    WordKeys,
    WordTypeValues,
)


def is_sound_event(word: Dict[str, Any]) -> bool:
    if word.get(WordKeys.TYPE) == WordTypeValues.AUDIO_EVENT:
        return True

    text = word.get(WordKeys.TEXT, word.get(WordKeys.WORD, '')).strip()
    return bool(re.match(r'^\(.*\)$', text))


def classify_segment(segment: Dict[str, Any]) -> str:
    words = segment.get(WordKeys.WORDS, [])
    if not words:
        return 'dialogue'

    has_sound = False
    has_dialogue = False

    for word in words:
        if is_sound_event(word):
            has_sound = True
        elif word.get(WordKeys.TYPE) not in [WordTypeValues.SPACING, '']:
            has_dialogue = True

    if has_sound and has_dialogue:
        return 'mixed'
    if has_sound:
        return 'sound_event'
    return 'dialogue'
