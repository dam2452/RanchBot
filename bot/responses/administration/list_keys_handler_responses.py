from typing import List

from bot.database.models import SubscriptionKey
from bot.responses.bot_response import BotResponse
from bot.utils.functions import convert_number_to_emoji


def create_subscription_keys_response(keys: List[SubscriptionKey]) -> str:
    key_lines = []

    for idx, key in enumerate(keys, start=1):
        line = f"{convert_number_to_emoji(idx)} | 🔑 Klucz: {key.key}\n   🕒 Ważność: {key.days} dni\n   📅 Utworzony: {key.timestamp or 'N/A'}"
        key_lines.append(line)

    response = "📃 Lista kluczy subskrypcji:\n"
    response += "```\n" + "\n\n".join(key_lines) + "\n```"
    return response


def get_subscription_keys_empty_message() -> str:
    return BotResponse.warning("BRAK KLUCZY SUBSKRYPCJI", "Brak zapisanych kluczy subskrypcji")


def get_log_subscription_keys_empty_message() -> str:
    return "Subscription keys list is empty."


def get_log_subscription_keys_sent_message() -> str:
    return "Subscription keys list sent to user."
