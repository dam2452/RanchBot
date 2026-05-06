from bot.responses.bot_response import BotResponse


def get_code_generated_message(token: str) -> str:
    return BotResponse.success(
        "KOD REJESTRACJI",
        f"Twoj jednorazowy kod do zalozenia konta REST API:\n\n{token}\n\nWazny przez 30 minut. Uzyj go na stronie podczas rejestracji.",
    )


def get_password_reset_code_message(code: str) -> str:
    return BotResponse.success(
        "KOD RESETU HASLA",
        f"Twoj jednorazowy kod do resetu hasla:\n\n{code}\n\nWazny przez 30 minut. Uzyj go na stronie w formularzu resetu hasla.",
    )
