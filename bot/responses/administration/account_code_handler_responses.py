from bot.responses.bot_response import BotResponse


def get_code_generated_message(token: str) -> str:
    return BotResponse.success(
        "KOD REJESTRACJI",
        f"Twoj jednorazowy kod do zalozenia konta REST API:\n\n{token}\n\nWazny przez 30 minut. Uzyj go na stronie podczas rejestracji.",
    )
