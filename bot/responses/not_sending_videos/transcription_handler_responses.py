from typing import Optional

from bot.types import TranscriptionContext
from bot.utils.constants import (
    EpisodeMetadataKeys,
    SegmentKeys,
    TranscriptionContextKeys,
)


def get_no_quote_provided_message() -> str:
    return "🔎 Podaj cytat, który chcesz znaleźć. Przykład: /transkrypcja Nie szkoda panu tego pięknego gabinetu?"


def get_transcription_response(
    quote: str,
    result: TranscriptionContext,
    snapped_start: Optional[float] = None,
    snapped_end: Optional[float] = None,
) -> str:
    def __format_time(seconds: float) -> str:
        minutes, secs = divmod(seconds, 60)
        return f"{int(minutes):02d}:{int(secs):02d}"

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
        f"⏰ *Czas: {__format_time(start_time)} - {__format_time(end_time)}* ⏰\n"
    )

    if snapped_start is not None and snapped_end is not None:
        response += f"🎞 *Scena: {__format_time(snapped_start)} - {__format_time(snapped_end)}* 🎞\n"

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
