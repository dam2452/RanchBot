def get_no_previous_searches_log() -> str:
    return "No previous search results found for user."

def get_no_quotes_selected_log() -> str:
    return "No segment selected by user."

def get_invalid_interval_log() -> str:
    return "End time must be later than start time."

def get_invalid_segment_log() -> str:
    return "Invalid segment index provided by user."

def get_extraction_failure_log() -> str:
    return "Failed to adjust video clip:"

def get_updated_segment_info_log(chat_id: int) -> str:
    return f"Updated segment info for chat ID '{chat_id}'"

def get_successful_adjustment_message(username: str) -> str:
    return f"Video clip adjusted successfully for user '{username}'."
