from collections import Counter
from dataclasses import (
    dataclass,
    field,
)
from pathlib import Path
import re
from typing import (
    Any,
    Dict,
    List,
)

from preprocessor.services.text.language_config import (
    ENGLISH_CONFIG,
    POLISH_CONFIG,
)


@dataclass
class TextStatistics:  # pylint: disable=too-many-instance-attributes  # Data structure for comprehensive text statistics - all attributes necessary
    text: str
    language: str = 'pl'

    avg_sentence_length: float = 0.0
    avg_word_length: float = 0.0
    bigrams: List[Dict[str, Any]] = field(default_factory=list)
    chars_without_spaces: int = 0
    consonants: int = 0
    digits: int = 0
    empty_lines: int = 0
    letter_frequency: Dict[str, int] = field(default_factory=dict)
    letters: int = 0
    lines: int = 0
    paragraphs: int = 0
    punctuation_marks: int = 0
    sentences: int = 0
    spaces: int = 0
    special_characters: int = 0
    symbols: int = 0
    total_chars: int = 0
    trigrams: List[Dict[str, Any]] = field(default_factory=list)
    type_token_ratio: float = 0.0
    unique_words: int = 0
    vowels: int = 0
    word_frequency: List[Dict[str, Any]] = field(default_factory=list)
    words: int = 0

    @classmethod
    def from_file(cls, file_path: Path, language: str = 'pl') -> 'TextStatistics':
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        stats = cls(text=text, language=language)
        stats.__process_calculations()
        return stats

    @classmethod
    def from_text(cls, text: str, language: str = 'pl') -> 'TextStatistics':
        stats = cls(text=text, language=language)
        stats.__process_calculations()
        return stats

    def to_dict(self) -> Dict[str, Any]:
        return {
            'basic_statistics': {
                'sentences': self.sentences,
                'lines': self.lines,
                'paragraphs': self.paragraphs,
                'empty_lines': self.empty_lines,
                'words': self.words,
                'letters': self.letters,
                'digits': self.digits,
                'symbols': self.symbols,
                'punctuation_marks': self.punctuation_marks,
                'special_characters': self.special_characters,
                'chars_without_spaces': self.chars_without_spaces,
                'spaces': self.spaces,
                'total_chars': self.total_chars,
                'vowels': self.vowels,
                'consonants': self.consonants,
            },
            'advanced_statistics': {
                'unique_words': self.unique_words,
                'avg_word_length': self.avg_word_length,
                'avg_sentence_length': self.avg_sentence_length,
                'type_token_ratio': self.type_token_ratio,
            },
            'letter_frequency': self.letter_frequency,
            'word_frequency': self.word_frequency,
            'bigrams': self.bigrams,
            'trigrams': self.trigrams,
        }

    def __process_calculations(self) -> None:  # pylint: disable=unused-private-member  # Called in from_file and from_text via name mangling - false positive
        self.__calculate_structural_stats()
        self.__calculate_character_distribution()
        self.__calculate_lexical_stats()
        self.__generate_n_grams()

    def __calculate_structural_stats(self) -> None:
        lines = self.text.split('\n')
        self.lines = len(lines)
        self.empty_lines = sum(1 for line in lines if not line.strip())

        paragraphs = self.text.split('\n\n')
        self.paragraphs = len([p for p in paragraphs if p.strip()])

        self.sentences = len(re.findall(r'[.!?…]+(?:\s|$)', self.text))
        self.total_chars = len(self.text)
        self.spaces = self.text.count(' ') + self.text.count('\t') + self.text.count('\n')
        self.chars_without_spaces = self.total_chars - self.spaces

    def __calculate_character_distribution(self) -> None:
        config = POLISH_CONFIG if self.language == 'pl' else ENGLISH_CONFIG
        letter_counter: Counter = Counter()

        for char in self.text:
            if char.isalpha():
                self.letters += 1
                char_lower = char.lower()
                letter_counter[char_lower] += 1
                if char in config.vowels:
                    self.vowels += 1
                elif char in config.consonants:
                    self.consonants += 1
            elif char.isdigit():
                self.digits += 1
            elif char in config.punctuation:
                self.punctuation_marks += 1
            elif char in config.special_chars:
                self.special_characters += 1
            elif not char.isspace():
                self.symbols += 1

        self.letter_frequency = dict(letter_counter.most_common())

    def __calculate_lexical_stats(self) -> None:
        words = self.__extract_words()
        self.words = len(words)

        if self.words > 0:
            word_counter = Counter(words)
            self.unique_words = len(word_counter)
            self.type_token_ratio = round(self.unique_words / self.words, 4)

            lengths = [len(w) for w in words]
            self.avg_word_length = round(sum(lengths) / self.words, 2)
            self.word_frequency = [{'word': w, 'count': c} for w, c in word_counter.most_common(50)]

            if self.sentences > 0:
                self.avg_sentence_length = round(self.words / self.sentences, 2)

    def __generate_n_grams(self) -> None:
        words = self.__extract_words()
        if len(words) >= 2:
            bigrams = Counter(zip(words[:-1], words[1:]))
            self.bigrams = [{'bigram': f'{w1} {w2}', 'count': c} for (w1, w2), c in bigrams.most_common(25)]

        if len(words) >= 3:
            trigrams = Counter(zip(words[:-2], words[1:-1], words[2:]))
            self.trigrams = [{'trigram': f'{w1} {w2} {w3}', 'count': c} for (w1, w2, w3), c in trigrams.most_common(25)]

    def __extract_words(self) -> List[str]:
        return re.findall(r'\b\w+\b', self.text.lower())
