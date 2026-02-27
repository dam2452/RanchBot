from bot.responses.bot_response import BotResponse


def get_clip_not_exist_message(clip_number: str) -> str:
    return BotResponse.error("KLIP NIE ISTNIEJE", f"Klip o nazwie '{clip_number}' nie istnieje")


def get_clip_id_not_exist_message(clip_id: int) -> str:
    return BotResponse.error("KLIP NIE ISTNIEJE", f"Klip o id {clip_id} nie istnieje")


def get_clip_deleted_message(clip_name: str) -> str:
    return BotResponse.success("KLIP USUNIĘTY", f"Klip '{clip_name}' został usunięty")


def get_no_saved_clips_message() -> str:
    return BotResponse.error("BRAK ZAPISANYCH KLIPÓW", "Nie masz żadnych zapisanych klipów")


def get_log_clip_not_exist_message(clip_number: int, username: str) -> str:
    return f"Clip '{clip_number}' does not exist for user '{username}'."


def get_log_clip_deleted_message(clip_name: str, username: str) -> str:
    return f"Clip '{clip_name}' has been successfully deleted for user '{username}'."


def get_log_no_saved_clips_message(username: str) -> str:
    return f"User '{username}' has no clips to delete."


def get_no_clip_number_provided_message() -> str:
    return BotResponse.usage(
        command="usunklip",
        error_title="BRAK NUMERU KLIPU",
        usage_syntax="<numer_klipu>",
        params=[("<numer_klipu>", "numer klipu z listy /mojeklipy")],
        example="/usunklip 2",
    )
