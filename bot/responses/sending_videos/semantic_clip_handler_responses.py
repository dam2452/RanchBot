from bot.responses.bot_response import BotResponse


def get_no_query_provided_message() -> str:
    return BotResponse.usage(
        command="senk",
        error_title="BRAK ZAPYTANIA",
        usage_syntax="[tryb] <zapytanie>",
        params=[
            ("[tryb]", "opcjonalnie: tekst (domyślnie), klatki"),
            ("<zapytanie>", "opis znaczenia/kontekstu do wyszukania (top wynik)"),
        ],
        example="/senk ucieczka od problemów | /senk klatki biesiada",
    )


def get_no_results_found_message(query: str) -> str:
    return BotResponse.warning("BRAK WYNIKÓW", f"Nie znaleziono wyników dla zapytania '{query}'.")


def get_no_video_path_message() -> str:
    return BotResponse.error("BRAK PLIKU", "Nie znaleziono ścieżki do pliku wideo dla tego segmentu.")


def get_log_semantic_clip_message(query: str, username: str, mode: str) -> str:
    return f"Semantic clip [{mode}] for '{query}' sent to user {username}."
