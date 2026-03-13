from bot.responses.bot_response import BotResponse


def get_no_report_content_message() -> str:
    return BotResponse.usage(
        command="report",
        error_title="BRAK TREŚCI RAPORTU",
        usage_syntax="<opis_problemu>",
        params=[("<opis_problemu>", "opis błędu lub sugestia ulepszenia")],
        example="/report Komenda /klip nie działa dla cytatu XYZ",
    )


def get_report_received_message() -> str:
    return BotResponse.success("ZGŁOSZENIE PRZYJĘTE", "Dziękujemy za zgłoszenie")


def get_log_no_report_content_message(username: str) -> str:
    return f"No report content provided by user '{username}'."


def get_log_report_received_message(username: str, report: str) -> str:
    return f"Report received from user '{username}': {report}"


def get_limit_exceeded_report_length_message() -> str:
    return BotResponse.error("LIMIT DŁUGOŚCI RAPORTU", "Przekroczono limit długości raportu")
