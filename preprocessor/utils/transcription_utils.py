from typing import (
    Any,
    Dict,
    List,
)


def convert_word_to_standard_format(word: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "text": word.get("word", word.get("text", "")).strip(),
        "start": word.get("start", 0.0),
        "end": word.get("end", 0.0),
        "type": "word",
        "speaker_id": word.get("speaker_id", "speaker_unknown"),
        "logprob": word.get("probability", 0.0),
    }


def convert_words_list(seg_words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [convert_word_to_standard_format(word) for word in seg_words]
