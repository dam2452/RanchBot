from typing import Dict

LANGUAGE_MAP = {
    "polish": "pl",
    "english": "en",
    "german": "de",
    "french": "fr",
    "spanish": "es",
}


def get_language_code(language: str) -> str:
    return LANGUAGE_MAP.get(language.lower(), language.lower())


def _process_whisper_segment(segment) -> Dict:
    words = []
    if hasattr(segment, 'words') and segment.words:
        for word in segment.words:
            words.append({
                "word": word.word,
                "start": word.start,
                "end": word.end,
                "probability": word.probability,
            })

    return {
        "id": segment.id,
        "seek": 0,
        "start": segment.start,
        "end": segment.end,
        "text": segment.text,
        "tokens": [],
        "avg_logprob": segment.avg_logprob,
        "compression_ratio": segment.compression_ratio,
        "no_speech_prob": segment.no_speech_prob,
        "words": words,
    }


def build_transcription_result(segments, language: str = None) -> Dict:
    result = {
        "text": "",
        "segments": [],
    }

    if language:
        result["language"] = language

    for segment in segments:
        segment_dict = _process_whisper_segment(segment)
        result["segments"].append(segment_dict)
        result["text"] += segment.text

    return result
