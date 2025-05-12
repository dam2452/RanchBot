def get_log_clip_name_exists_message(clip_name: str, username: str) -> str:
    return f"Clip name '{clip_name}' already exists for user '{username}'."


def get_log_no_segment_selected_message() -> str:
    return "No segment selected, manual clip, or compiled clip available for user."


def get_log_failed_to_verify_clip_length_message(clip_name: str, username: str) -> str:
    return f"Failed to verify the length of the clip '{clip_name}' for user '{username}'."


def get_log_clip_saved_successfully_message(clip_name: str, username: str) -> str:
    return f"Clip '{clip_name}' saved successfully for user '{username}'."

def get_log_clip_name_numeric_message(clip_name: str, username: str) -> str:
    return f"Clip name '{clip_name}' consists only of digits for user '{username}'. Not allowed."
