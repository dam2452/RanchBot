import difflib
from typing import (
    Dict,
    List,
    Optional,
)

from bot.responses.bot_response import BotResponse
from bot.types import EmotionInfo
from bot.utils.functions import convert_number_to_emoji

_EMOTION_EN_TO_PL: Dict[str, str] = {
    "happiness": "radosny",
    "sadness": "smutny",
    "anger": "zly",
    "surprise": "zaskoczony",
    "disgust": "obrzydzony",
    "fear": "przestraszony",
    "neutral": "neutralny",
    "contempt": "pogardliwy",
}
_EMOTION_PL_TO_EN: Dict[str, str] = {v: k for k, v in _EMOTION_EN_TO_PL.items()}


def map_emotion_to_pl(label_en: str) -> str:
    return _EMOTION_EN_TO_PL.get(label_en.lower(), label_en)


def map_emotion_to_en(label: str) -> Optional[str]:
    lower = label.lower()
    if lower in _EMOTION_EN_TO_PL:
        return lower
    if lower in _EMOTION_PL_TO_EN:
        return _EMOTION_PL_TO_EN[lower]
    all_labels = list(_EMOTION_EN_TO_PL.keys()) + list(_EMOTION_PL_TO_EN.keys())
    matches = difflib.get_close_matches(lower, all_labels, n=1, cutoff=0.5)
    if not matches:
        return None
    matched = matches[0]
    return matched if matched in _EMOTION_EN_TO_PL else _EMOTION_PL_TO_EN[matched]


def format_emotions_list(emotions: List[EmotionInfo]) -> str:
    if not emotions:
        return get_no_emotions_message()
    lines = [
        f"{convert_number_to_emoji(i + 1)}  {e['label_pl']} ({e['label_en']})"
        for i, e in enumerate(emotions)
    ]
    body = f"Łącznie: {convert_number_to_emoji(len(emotions))} emocji\n\n" + "\n".join(lines)
    return BotResponse.info("DOSTĘPNE EMOCJE", body)


def get_no_emotions_message() -> str:
    return BotResponse.warning("BRAK DANYCH", "Brak danych o emocjach w indeksie.")


def get_invalid_args_count_message() -> str:
    return BotResponse.usage(
        command="emocje",
        error_title="ZA DUŻO ARGUMENTÓW",
        usage_syntax="",
        params=[],
        example="/emocje",
    )


def get_log_emotions_listed_message(count: int, username: str) -> str:
    return f"Emotions list ({count} items) sent to user {username}."
