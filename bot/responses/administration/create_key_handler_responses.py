from bot.responses.bot_response import BotResponse


def get_invalid_args_message() -> str:
    return BotResponse.usage(
        command="addkey",
        error_title="BRAK ARGUMENTÓW",
        usage_syntax="<dni> <klucz>",
        params=[
            ("<dni>", "liczba dni subskrypcji (liczba całkowita)"),
            ("<klucz>", "treść klucza subskrypcyjnego"),
        ],
        example="/addkey 30 tajny_klucz",
    )


def get_create_key_success_message(days: int, key: str) -> str:
    return BotResponse.success("KLUCZ STWORZONY", f"Stworzono klucz: {key} na {days} dni")


def get_key_already_exists_message(key: str) -> str:
    return BotResponse.error("KLUCZ ISTNIEJE", f"Klucz {key} już istnieje")
