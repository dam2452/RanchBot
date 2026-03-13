from typing import (
    Any,
    Dict,
    List,
)

from bot.responses.bot_response import BotResponse
from bot.utils.constants import EpisodeMetadataKeys
from bot.utils.functions import (
    convert_number_to_emoji,
    format_segment,
)


def format_semantic_search_response(
    unique_count: int,
    results: List[Dict[str, Any]],
    query: str,
) -> str:
    emoji_count = convert_number_to_emoji(unique_count)
    response = (
        f"🧠 *Wyniki wyszukiwania semantycznego* 🧠\n"
        f"👁️ *Znaleziono:* {emoji_count} pasujących cytatów 👁️\n\n"
    )
    segment_lines = []

    for i, segment in enumerate(results[:5], start=1):
        segment_info = format_segment(segment)
        line = (
            f"{convert_number_to_emoji(i)}  | 📺 {segment_info.episode_formatted} | 🕒 {segment_info.time_formatted}\n"
            f"   👉  {segment_info.episode_title}"
        )
        segment_lines.append(line)

    response += f"```Zapytanie: \"{query}\" \n".replace(" ", "\u00A0") + "\n\n".join(segment_lines) + "\n```"
    return response


def format_semantic_frames_response(
    unique_count: int,
    frames: List[Dict[str, Any]],
    query: str,
) -> str:
    emoji_count = convert_number_to_emoji(unique_count)
    response = (
        f"🎞️ *Wyniki wyszukiwania semantycznego — klatki* 🎞️\n"
        f"👁️ *Znaleziono:* {emoji_count} pasujących scen 👁️\n\n"
    )
    frame_lines = []

    for i, frame in enumerate(frames[:5], start=1):
        segment_info = format_segment(frame)
        line = (
            f"{convert_number_to_emoji(i)}  | 📺 {segment_info.episode_formatted} | 🕒 {segment_info.time_formatted}\n"
            f"   👉  {segment_info.episode_title}"
        )
        frame_lines.append(line)

    response += f"```Zapytanie: \"{query}\" \n".replace(" ", "\u00A0") + "\n\n".join(frame_lines) + "\n```"
    return response


def format_semantic_episodes_response(
    unique_count: int,
    episodes: List[Dict[str, Any]],
    query: str,
) -> str:
    emoji_count = convert_number_to_emoji(unique_count)
    response = (
        f"📼 *Wyniki wyszukiwania semantycznego — odcinki* 📼\n"
        f"👁️ *Znaleziono:* {emoji_count} pasujących odcinków 👁️\n\n"
    )
    episode_lines = []

    for i, ep in enumerate(episodes[:5], start=1):
        meta = ep.get(EpisodeMetadataKeys.EPISODE_METADATA, {})
        season = meta.get(EpisodeMetadataKeys.SEASON)
        episode_num = meta.get(EpisodeMetadataKeys.EPISODE_NUMBER)
        title = meta.get(EpisodeMetadataKeys.TITLE, "")

        if season == 0:
            ep_fmt = f"Spec-{episode_num}"
        else:
            ep_fmt = f"S{str(season).zfill(2)}E{str(episode_num).zfill(2)}"

        line = (
            f"{convert_number_to_emoji(i)}  | 📺 {ep_fmt}\n"
            f"   👉  {title}"
        )
        episode_lines.append(line)

    response += f"```Zapytanie: \"{query}\" \n".replace(" ", "\u00A0") + "\n\n".join(episode_lines) + "\n```"
    return response


def get_no_query_provided_message() -> str:
    return BotResponse.usage(
        command="sens",
        error_title="BRAK ZAPYTANIA",
        usage_syntax="[tryb] <zapytanie>",
        params=[
            ("[tryb]", "opcjonalnie: tekst (domyślnie), klatki, odcinek"),
            ("<zapytanie>", "opis znaczenia/kontekstu do wyszukania (5 wyników)"),
        ],
        example="/sens ucieczka od problemów | /sens klatki biesiada | /sens odcinek ślub",
    )


def get_vllm_unavailable_message() -> str:
    return "Serwis embeddingów chwilowo niedostępny. Spróbuj /sz zamiast /sens."


def get_embeddings_not_indexed_message(series_name: str, mode: str) -> str:
    return BotResponse.warning(
        "BRAK EMBEDDINGÓW",
        f"Embeddingi ({mode}) dla serialu '{series_name}' nie zostaly jeszcze wygenerowane.",
    )


def get_log_semantic_search_results_sent_message(query: str, username: str, mode: str) -> str:
    return f"Semantic search [{mode}] results for '{query}' sent to '{username}'."
