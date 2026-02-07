from bot.types import TranscriptionContext


def get_no_quote_provided_message() -> str:
    return "🔎 Podaj cytat, który chcesz znaleźć. Przykład: /transkrypcja Nie szkoda panu tego pięknego gabinetu?"


def get_transcription_response(quote: str, result: TranscriptionContext) -> str:
    start_time = float(result["overall_start_time"])
    end_time = float(result["overall_end_time"])

    target = result.get("target", {})
    episode_info = target.get("episode_metadata", target.get("episode_info", {}))

    season = episode_info.get("season")
    episode_number = episode_info.get("episode_number")
    episode_title = episode_info.get("title")

    if not isinstance(season, int) or not isinstance(episode_number, int) or not isinstance(episode_title, str):
        raise TypeError("Invalid type detected in episode metadata. Expected types: int for season and episode_number, str for title.")

    if season == 0:
        episode_display = f"Spec-{episode_number}"
        absolute_episode_display = episode_display
    else:
        episode_display = f"S{int(season):02d}E{int(episode_number):02d}"
        absolute_episode_display = str((season - 1) * 13 + episode_number)

    start_minutes, start_seconds = divmod(start_time, 60)
    end_minutes, end_seconds = divmod(end_time, 60)

    response = (
        f"📺 *{episode_title}* 📺\n"
        f"🎬 *{episode_display} ({absolute_episode_display})* 🎬\n"
        f"⏰ *Czas: {int(start_minutes):02d}:{int(start_seconds):02d} - {int(end_minutes):02d}:{int(end_seconds):02d}* ⏰\n\n"
        "```"
    )

    response += f"Cytat: \"{quote}\" \n".replace(" ", "\u00A0")

    target = result['target']
    target_id = target.get('segment_id', target.get('id'))
    for segment in result["context"]:
        segment_id = int(segment['id'])
        if segment_id == target_id:
            response += f"💥🆔 {segment_id} - {segment['text']} 💥\n"
        else:
            response += f"🆔 {segment_id} - {segment['text']}\n"

    response += "```"

    return response


def get_log_transcription_response_sent_message(quote: str, username: str) -> str:
    return f"Transcription for quote '{quote}' sent to user '{username}'."
