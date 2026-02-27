from bot.responses.bot_response import BotResponse
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


def get_incorrect_season_episode_format_message() -> str:
    return BotResponse.error(
        "NIEPRAWIDŁOWY FORMAT ODCINKA",
        "Użyj formatu SxxEyy, np. S02E10 (S02 = sezon 2, E10 = odcinek 10)",
    )


def get_video_file_not_exist_message() -> str:
    return BotResponse.error(
        "PLIK WIDEO NIE ISTNIEJE",
        "Sprawdź poprawność sezonu i odcinka, np. S02E10",
    )


def get_incorrect_time_format_message() -> str:
    return BotResponse.error(
        "NIEPRAWIDŁOWY FORMAT CZASU",
        "Użyj formatu MM:SS.ms\nPrzykład: 20:30.11 (20 minut, 30 sekund, 11 ms)",
    )


def get_end_time_earlier_than_start_message() -> str:
    return BotResponse.error(
        "CZAS ZAKOŃCZENIA PRZED STARTEM",
        "Czas start musi być wcześniejszy niż koniec\nPrzykład: 20:30.11 (start) wcześniejszy niż 21:32.50 (koniec)",
    )


def get_limit_exceeded_clip_duration_message() -> str:
    return BotResponse.error("LIMIT DŁUGOŚCI KLIPU", "Przekroczono maksymalną długość klipu")


def get_no_args_provided_message() -> str:
    return BotResponse.usage(
        command="wytnij",
        error_title="BRAK ARGUMENTÓW",
        usage_syntax="<sezon_odcinek> <czas_start> <czas_koniec>",
        params=[
            ("<sezon_odcinek>", "format SxxEyy, np. S07E06"),
            ("<czas_start>", "format MM:SS.ms, np. 36:47.50"),
            ("<czas_koniec>", "format MM:SS.ms, np. 36:49.00"),
        ],
        example="/wytnij S07E06 36:47.50 36:49.00",
    )
