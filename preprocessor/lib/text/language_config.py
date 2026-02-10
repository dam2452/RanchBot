from dataclasses import dataclass
from typing import Set


@dataclass
class LanguageConfig:
    vowels: Set[str]
    consonants: Set[str]
    punctuation: Set[str]
    special_chars: Set[str]
POLISH_VOWELS = set('aąeęioóuyAĄEĘIOÓUY')
POLISH_CONSONANTS = set('bcćdfghjklłmnńprsśtwzźżBCĆDFGHJKLŁMNŃPRSŚTWZŹŻ')
ENGLISH_VOWELS = set('aeiouAEIOU')
ENGLISH_CONSONANTS = set('bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ')
PUNCTUATION = set('.,;:!?…-—–()[]{}"\'«»„\'\'')
SPECIAL_CHARS = set('@#$%^&*+=<>|\\/_~`')
POLISH_CONFIG = LanguageConfig(
    vowels=POLISH_VOWELS | ENGLISH_VOWELS,
    consonants=POLISH_CONSONANTS | ENGLISH_CONSONANTS,
    punctuation=PUNCTUATION,
    special_chars=SPECIAL_CHARS,
)
ENGLISH_CONFIG = LanguageConfig(
    vowels=ENGLISH_VOWELS,
    consonants=ENGLISH_CONSONANTS,
    punctuation=PUNCTUATION,
    special_chars=SPECIAL_CHARS,
)
