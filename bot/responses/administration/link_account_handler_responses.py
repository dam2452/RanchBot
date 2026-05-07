from bot.responses.bot_response import BotResponse


def get_invalid_args_message() -> str:
    return BotResponse.usage(
        command="link",
        error_title="BŁĘDNE ARGUMENTY",
        usage_syntax="<kod>",
        params=[
            ("<kod>", "kod łączenia konta z REST API"),
        ],
        example="/link ABCD1234",
    )


def get_link_success_message(username: str) -> str:
    return BotResponse.success("KONTO POŁĄCZONE", f"Twoje konto Telegram zostało połączone z kontem REST API: {username}")


def get_invalid_code_message() -> str:
    return BotResponse.error("NIEPRAWIDŁOWY KOD", "Kod jest nieprawidłowy, wygasł lub został już użyty.")


def get_already_linked_message() -> str:
    return BotResponse.error("KONTO POŁĄCZONE", "Twoje konto Telegram jest już połączone z kontem REST API.")
