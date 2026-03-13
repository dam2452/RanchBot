from bot.responses.bot_response import BotResponse


def get_sd_invalid_args_count_message() -> str:
    return BotResponse.usage(
        command="sd",
        error_title="BRAK ARGUMENTÓW",
        usage_syntax="<ile_cięć_wstecz> <ile_cięć_naprzód>",
        params=[
            ("<ile_cięć_wstecz>", "liczba cięć scen do cofnięcia"),
            ("<ile_cięć_naprzód>", "liczba cięć scen do przejścia"),
        ],
        example="/sd 1 1",
    )


def get_sd_no_scene_cuts_message() -> str:
    return BotResponse.warning("BRAK DANYCH O CIĘCIACH SCEN", "Brak danych o cięciach scen dla tego odcinka")
