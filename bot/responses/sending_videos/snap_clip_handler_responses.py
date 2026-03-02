def get_no_last_clip_message() -> str:
    return "⚠️ Brak ostatniego klipu. Najpierw wykonaj /klip lub /wybierz."


def get_no_adjusted_times_message() -> str:
    return "⚠️ Ostatni klip nie ma zapisanych czasów. Użyj /klip lub /wybierz."


def get_already_snapped_message() -> str:
    return "✅ Klip jest już wyrównany do cięć scen."


def get_no_scene_cuts_message() -> str:
    return "⚠️ Brak danych o cięciach scen dla tego epizodu."


def get_snap_success_log(username: str) -> str:
    return f"Clip snapped to scene cuts for user '{username}'."


def get_snap_success_message(old_start: float, old_end: float, new_start: float, new_end: float) -> str:
    return (
        f"✅ Klip wyrównany do cięć scen.\n"
        f"Stary zakres: {old_start:.2f}s - {old_end:.2f}s\n"
        f"Nowy zakres: {new_start:.2f}s - {new_end:.2f}s"
    )
