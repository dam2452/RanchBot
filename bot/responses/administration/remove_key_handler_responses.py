from bot.responses.bot_response import BotResponse


def get_remove_key_success_message(key: str) -> str:
    return BotResponse.success("KLUCZ USUNIĘTY", f"Klucz '{key}' został usunięty")


def get_remove_key_failure_message(key: str) -> str:
    return BotResponse.error("KLUCZ NIE ZNALEZIONY", f"Nie znaleziono klucza '{key}'")


def get_no_key_provided_message() -> str:
    return BotResponse.usage(
        command="removekey",
        error_title="BRAK KLUCZA",
        usage_syntax="<klucz>",
        params=[("<klucz>", "treść klucza do usunięcia")],
        example="/removekey tajny_klucz",
    )
