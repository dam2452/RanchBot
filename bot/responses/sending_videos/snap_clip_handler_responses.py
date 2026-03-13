from bot.responses.bot_response import BotResponse


def get_no_last_clip_message() -> str:
    return BotResponse.warning("BRAK OSTATNIEGO KLIPU", "Brak ostatniego klipu. Najpierw wykonaj /klip lub /wybierz")


def get_no_adjusted_times_message() -> str:
    return BotResponse.warning("BRAK CZASU KLIPU", "Ostatni klip nie ma zapisanych czasów. Użyj /klip lub /wybierz")


def get_already_snapped_message() -> str:
    return BotResponse.info("JUŻ WYRÓWNANY", "Klip jest już wyrównany do cięć scen")


def get_no_scene_cuts_message() -> str:
    return BotResponse.warning("BRAK DANYCH O CIĘCIACH SCEN", "Brak danych o cięciach scen dla tego epizodu")


def get_snap_success_log(username: str) -> str:
    return f"Clip snapped to scene cuts for user '{username}'."


def get_snap_success_message(old_start: float, old_end: float, new_start: float, new_end: float) -> str:
    body = (
        f"Stary zakres: {old_start:.2f}s - {old_end:.2f}s\n"
        f"Nowy zakres: {new_start:.2f}s - {new_end:.2f}s"
    )
    return BotResponse.success("KLIP WYRÓWNANY", body)
