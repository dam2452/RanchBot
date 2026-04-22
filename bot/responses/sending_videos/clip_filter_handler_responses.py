def get_log_clip_filter_success_message(chat_id: int, username: str) -> str:
    return f"Clip-from-filter delivered to chat_id={chat_id} (user={username})."


def get_log_clip_filter_no_results_message(chat_id: int) -> str:
    return f"Clip-from-filter: no segments matched filter for chat_id={chat_id}."
