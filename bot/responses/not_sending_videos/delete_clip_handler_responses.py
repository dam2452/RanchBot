def get_log_clip_not_exist_message(clip_number: int, username: str) -> str:
    return f"Clip with index '{clip_number}' does not exist for user '{username}'."


def get_log_clip_deleted_message(clip_name: str, username: str) -> str:
    return f"Clip '{clip_name}' has been successfully deleted for user '{username}'."


def get_log_clip_name_not_found_message(clip_name: str, username: str) -> str:
    return f"Clip with name '{clip_name}' not found for user '{username}'."

def get_log_no_saved_clips_message(username: str) -> str:
    return f"User '{username}' has no clips to delete."

def get_log_invalid_args_count_message(username: str, error_message: str) -> str:
    return f"Invalid arguments for DeleteClipHandler by {username}. Message: '{error_message}'"
