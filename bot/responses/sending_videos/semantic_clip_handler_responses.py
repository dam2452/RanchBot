from bot.responses.bot_response import BotResponse


def get_no_query_provided_message() -> str:
    return BotResponse.usage(
        command="senk",
        error_title="BRAK ZAPYTANIA",
        usage_syntax="[tryb] <zapytanie>",
        params=[
            ("[tryb]", "opcjonalnie: tekst (domyślnie), klatki, odcinek"),
            ("<zapytanie>", "opis znaczenia/kontekstu do wyszukania (top wynik)"),
        ],
        example="/senk ucieczka od problemów | /senk klatki biesiada | /senk odcinek ślub",
    )


def get_no_results_found_message(query: str) -> str:
    return BotResponse.warning("BRAK WYNIKÓW", f"Nie znaleziono wyników dla zapytania '{query}'.")


def get_log_semantic_clip_message(query: str, username: str, mode: str) -> str:
    return f"Semantic clip [{mode}] for '{query}' sent to user {username}."
