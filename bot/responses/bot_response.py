from typing import (
    List,
    Tuple,
)


class BotResponse:
    __NBSP = "\u00A0"

    @staticmethod
    def __to_code_block(header: str, body: str) -> str:
        content = f"```{header}\n\n{body}```"
        return content.replace(" ", BotResponse.__NBSP)

    @staticmethod
    def error(title: str, body: str) -> str:
        return BotResponse.__to_code_block(f"❌ BŁĄD - {title}", body)

    @staticmethod
    def warning(title: str, body: str) -> str:
        return BotResponse.__to_code_block(f"⚠️ OSTRZEŻENIE - {title}", body)

    @staticmethod
    def info(title: str, body: str) -> str:
        return BotResponse.__to_code_block(f"ℹ️ INFO - {title}", body)

    @staticmethod
    def success(title: str, body: str) -> str:
        return BotResponse.__to_code_block(f"✅ SUKCES - {title}", body)

    @staticmethod
    def usage(
        command: str,
        error_title: str,
        usage_syntax: str,
        params: List[Tuple[str, str]],
        example: str,
    ) -> str:
        params_str = "\n".join(f"• {name} - {desc}" for name, desc in params)
        body = (
            f"📋 Użycie:\n"
            f"   /{command} {usage_syntax}\n\n"
            f"📌 Parametry:\n"
            f"{params_str}\n\n"
            f"💡 Przykład:\n"
            f"   {example}"
        )
        return BotResponse.__to_code_block(f"❌ BŁĄD - {error_title}", body)
