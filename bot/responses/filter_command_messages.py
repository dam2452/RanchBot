from bot.responses.bot_response import BotResponse


def get_no_filter_set_message() -> str:
    return BotResponse.warning(
        "BRAK AKTYWNEGO FILTRA",
        (
            "Ustaw najpierw filtr (np. /filtr postac:Pawlak emocja:happy sezon:3).\n"
            "Listę dostępnych opcji znajdziesz w /filtr help."
        ),
    )


def get_no_segments_match_active_filter_message() -> str:
    return BotResponse.warning(
        "BRAK WYNIKÓW",
        "Żaden segment nie pasuje do aktywnego filtra. Sprawdź /filtr info i ewentualnie rozluźnij kryteria.",
    )
