from bot.video.episode import Episode


def get_log_incorrect_season_episode_format_message() -> str:
    return "Incorrect season/episode format provided by user."


def get_log_video_file_not_exist_message(video_path: str) -> str:
    return f"Video file does not exist: {video_path}"


def get_log_incorrect_time_format_message() -> str:
    return "Incorrect time format provided by user."


def get_log_end_time_earlier_than_start_message() -> str:
    return "End time must be later than start time."


def get_log_clip_extracted_message(episode: Episode, start_seconds: float, end_seconds: float) -> str:
    return f"Clip extracted and sent for command: /wytnij {episode} {start_seconds} {end_seconds}"


def get_invalid_args_count_message() -> str:
    return (
        "📋 **Poprawne użycie komendy**: /wytnij `<sezon_odcinek>` `<czas_start>` `<czas_koniec>`.\n"
        "Przykład: /wytnij S07E06 36:47.50 36:49.00\n"
        "Upewnij się, że podałeś poprawnie wszystkie trzy elementy: sezon_odcinek, czas_start i czas_koniec."
    )


def get_incorrect_season_episode_format_message() -> str:
    return (
        "❌ **Błędny format sezonu i odcinka!** Użyj formatu **SxxEyy**.\n"
        "Przykład: **S02E10**, gdzie **S02** oznacza sezon 2, a **E10** oznacza odcinek 10.\n"
        "🔎 **Zwróć uwagę na dwukropek** między literami S i E oraz na cyfry."
    )


def get_video_file_not_exist_message() -> str:
    return (
        "❌ **Nie znaleziono pliku wideo** dla podanego sezonu i odcinka.\n"
        "Sprawdź, czy podałeś poprawny sezon i odcinek, np. **S02E10**."
    )


def get_incorrect_time_format_message() -> str:
    return (
        "❌ **Błędny format czasu!** Użyj formatu **MM:SS\u200B.ms**.\n\n"
        "Przykład: **20:30.11**, gdzie **20:30.11** oznacza 20 minut, 30 sekund i 11 milisekund.\n\n"
        "🔎 **Zwróć uwagę na dwukropek** między minutami i sekundami oraz **kropkę** przed milisekundami."
    )


def get_end_time_earlier_than_start_message() -> str:
    return (
        "❌ Czas zakończenia musi być późniejszy niż czas rozpoczęcia!\n"
        "Upewnij się, że czas_start jest wcześniejszy niż czas_koniec.\n"
        "Przykład: 20:30.11 (czas_start) powinno być wcześniejsze niż 21:32.50 (czas_koniec)."
    )


def get_limit_exceeded_clip_duration_message() -> str:
    return "❌ Przekroczono limit długości klipu! ❌ \n"
