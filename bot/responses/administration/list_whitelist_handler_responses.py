from typing import List

from bot.database.models import UserProfile
from bot.responses.bot_response import BotResponse
from bot.utils.functions import format_user_list


def create_whitelist_response(users: List[UserProfile]) -> str:
    return format_user_list(users, "Lista użytkowników w Whitelist")


def get_whitelist_empty_message() -> str:
    return BotResponse.warning("WHITELIST PUSTA", "Whitelist jest pusta")


def get_log_whitelist_empty_message() -> str:
    return "Whitelist is empty."


def get_log_whitelist_sent_message() -> str:
    return "Whitelist sent to user."
