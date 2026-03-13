from bot.responses.bot_response import BotResponse


def get_log_segment_saved_message(chat_id: int) -> str:
    return f"Segment saved as last selected for chat ID '{chat_id}'"


def get_log_clip_success_message(username: str) -> str:
    return f"Video clip extracted successfully for user '{username}'."


def get_no_segments_found_message() -> str:
    return BotResponse.error("BRAK WYNIKÓW", "Nie znaleziono pasujących cytatów")


def get_limit_exceeded_clip_duration_message() -> str:
    return BotResponse.error("LIMIT DŁUGOŚCI KLIPU", "Przekroczono maksymalną długość klipu")


def get_message_too_long_message() -> str:
    return BotResponse.error("WIADOMOŚĆ ZA DŁUGA", "Skróć treść wiadomości")


def get_no_quote_provided_message() -> str:
    return BotResponse.usage(
        command="klip",
        error_title="BRAK CYTATU",
        usage_syntax="<cytat>",
        params=[("<cytat>", "fragment tekstu do wyszukania")],
        example="/klip geniusz",
    )
