from typing import Optional

from bot.responses.bot_response import BotResponse
from bot.types import TranscriptionContext
from bot.utils.constants import (
    EpisodeMetadataKeys,
    SegmentKeys,
    TranscriptionContextKeys,
)
from bot.utils.functions import format_seconds_to_mmss


def get_transcription_response(
    quote: str,
    result: TranscriptionContext,
    snapped_start: Optional[float] = None,
    snapped_end: Optional[float] = None,
) -> str:
    start_time = float(result[TranscriptionContextKeys.OVERALL_START_TIME])
    end_time = float(result[TranscriptionContextKeys.OVERALL_END_TIME])

    target = result.get(TranscriptionContextKeys.TARGET, {})
    episode_info = target.get(
        EpisodeMetadataKeys.EPISODE_METADATA,
        target.get(EpisodeMetadataKeys.EPISODE_INFO, {}),
    )

    season = episode_info.get(EpisodeMetadataKeys.SEASON)
    episode_number = episode_info.get(EpisodeMetadataKeys.EPISODE_NUMBER)
    episode_title = episode_info.get(EpisodeMetadataKeys.TITLE)

    if not isinstance(season, int) or not isinstance(episode_number, int) or not isinstance(episode_title, str):
        raise TypeError("Invalid type detected in episode metadata. Expected types: int for season and episode_number, str for title.")

    if season == 0:
        episode_display = f"Spec-{episode_number}"
        absolute_episode_display = episode_display
    else:
        episode_display = f"S{int(season):02d}E{int(episode_number):02d}"
        absolute_episode_display = str((season - 1) * 13 + episode_number)

    response = (
        f"📺 *{episode_title}* 📺\n"
        f"🎬 *{episode_display} ({absolute_episode_display})* 🎬\n"
        f"⏰ *Czas: {format_seconds_to_mmss(start_time)} - {format_seconds_to_mmss(end_time)}* ⏰\n"
    )

    if snapped_start is not None and snapped_end is not None:
        response += f"🎞 *Scena: {format_seconds_to_mmss(snapped_start)} - {format_seconds_to_mmss(snapped_end)}* 🎞\n"

    response += "\n```"

    response += f"Cytat: \"{quote}\" \n".replace(" ", "\u00A0")

    target = result[TranscriptionContextKeys.TARGET]
    target_id = target.get(SegmentKeys.SEGMENT_ID, target.get(SegmentKeys.ID))
    for segment in result[TranscriptionContextKeys.CONTEXT]:
        segment_id = int(segment[SegmentKeys.ID])
        if segment_id == target_id:
            response += f"💥🆔 {segment_id} - {segment[SegmentKeys.TEXT]} 💥\n"
        else:
            response += f"🆔 {segment_id} - {segment[SegmentKeys.TEXT]}\n"

    response += "```"

    return response


def get_log_transcription_response_sent_message(quote: str, username: str) -> str:
    return f"Transcription for quote '{quote}' sent to user '{username}'."


def get_no_quote_provided_message() -> str:
    return BotResponse.usage(
        command="transkrypcja",
        error_title="BRAK CYTATU",
        usage_syntax="<cytat>",
        params=[("<cytat>", "fragment tekstu do wyszukania transkrypcji")],
        example="/transkrypcja geniusz",
    )
