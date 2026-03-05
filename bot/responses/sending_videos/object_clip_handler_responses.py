from bot.responses.bot_response import BotResponse


def get_no_object_provided_message() -> str:
    return BotResponse.usage(
        command="ko",
        error_title="BRAK OBIEKTU",
        usage_syntax="<obiekt>",
        params=[
            ("<obiekt>", "nazwa obiektu (fuzzy, wymagana)"),
        ],
        example="/ko dog",
    )


def get_object_not_found_message(object_query: str) -> str:
    return BotResponse.warning("BRAK WYNIKÓW", f"Nie znaleziono obiektu pasującego do '{object_query}'.")


def get_no_scenes_found_message(object_name: str) -> str:
    return BotResponse.warning("BRAK WYNIKÓW", f"Nie znaleziono scen z obiektem '{object_name}'.")


def get_log_object_clip_message(object_name: str, username: str) -> str:
    return f"Object clip for '{object_name}' sent to user {username}."
