from typing import (
    Dict,
    List,
    Optional,
)

from bot.responses.bot_response import BotResponse
from bot.types import EmotionInfo

EMOTION_PL_MAP: Dict[str, str] = {
    "happy": "radosny",
    "sad": "smutny",
    "angry": "zly",
    "surprised": "zaskoczony",
    "disgusted": "obrzydzony",
    "disgust": "obrzydzony",
    "fear": "przestraszony",
    "fearful": "przestraszony",
    "neutral": "neutralny",
    "contempt": "pogardliwy",
    "confused": "zdezorientowany",
    "calm": "spokojny",
    "excited": "podekscytowany",
}


def map_emotion_to_pl(label_en: str) -> str:
    return EMOTION_PL_MAP.get(label_en.lower(), label_en)


def map_emotion_to_en(label: str) -> Optional[str]:
    lower = label.lower()
    if lower in EMOTION_PL_MAP:
        return lower
    reverse = {v: k for k, v in EMOTION_PL_MAP.items()}
    return reverse.get(lower)


def format_emotions_list(emotions: List[EmotionInfo]) -> str:
    if not emotions:
        return get_no_emotions_message()
    lines = [f"{e['label_pl']} ({e['label_en']})" for e in emotions]
    header = f"Dostepne emocje ({len(emotions)}):\n\n"
    return header + "\n".join(f"{i + 1}. {line}" for i, line in enumerate(lines))


def get_no_emotions_message() -> str:
    return "Brak danych o emocjach w indeksie."


def get_invalid_args_count_message() -> str:
    return BotResponse.usage(
        command="emocje",
        error_title="ZA DUZO ARGUMENTOW",
        usage_syntax="",
        params=[],
        example="/emocje",
    )


def get_log_emotions_listed_message(count: int, username: str) -> str:
    return f"Emotions list ({count} items) sent to user {username}."
