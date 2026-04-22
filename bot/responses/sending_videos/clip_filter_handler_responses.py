from bot.responses.bot_response import BotResponse


def get_clip_filter_usage_message() -> str:
    return BotResponse.usage(
        command="kf",
        error_title="SKŁADNIA",
        usage_syntax="[cytat]",
        params=[
            ("[cytat]", "opcjonalnie — jak /klip: wyszukuje fragment w transkrypcjach"),
            ("(bez cytatu)", "używa aktywnego filtra z /filtr — jak dotychczas"),
        ],
        example="/kf geniusz",
    )


def get_log_clip_filter_success_message(chat_id: int, username: str) -> str:
    return f"Clip-from-filter delivered to chat_id={chat_id} (user={username})."


def get_log_clip_filter_no_results_message(chat_id: int) -> str:
    return f"Clip-from-filter: no segments matched filter for chat_id={chat_id}."
