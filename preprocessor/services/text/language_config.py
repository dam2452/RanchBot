from dataclasses import dataclass
from typing import Set


@dataclass(frozen=True)
class LanguageConfig:
    consonants: Set[str]
    punctuation: Set[str]
    special_chars: Set[str]
    vowels: Set[str]


_PUNCTUATION = set('.,;:!?…-—–()[]{}"\'«»„\'\'')
_SPECIAL_CHARS = set('@#$%^&*+=<>|\\/_~`')
_ENGLISH_VOWELS = set('aeiouAEIOU')
_ENGLISH_CONSONANTS = set('bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ')
_POLISH_VOWELS = set('aąeęioóuyAĄEĘIOÓUY')
_POLISH_CONSONANTS = set('bcćdfghjklłmnńprsśtwzźżBCĆDFGHJKLŁMNŃPRSŚTWZŹŻ')

POLISH_CONFIG = LanguageConfig(
    vowels=_POLISH_VOWELS | _ENGLISH_VOWELS,
    consonants=_POLISH_CONSONANTS | _ENGLISH_CONSONANTS,
    punctuation=_PUNCTUATION,
    special_chars=_SPECIAL_CHARS,
)

ENGLISH_CONFIG = LanguageConfig(
    vowels=_ENGLISH_VOWELS,
    consonants=_ENGLISH_CONSONANTS,
    punctuation=_PUNCTUATION,
    special_chars=_SPECIAL_CHARS,
)
