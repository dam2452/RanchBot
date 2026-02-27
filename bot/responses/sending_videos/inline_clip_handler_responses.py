from bot.responses.bot_response import BotResponse


def get_no_query_provided_message() -> str:
    return BotResponse.usage(
        command="inline",
        error_title="BRAK ZAPYTANIA",
        usage_syntax="<cytat>",
        params=[("<cytat>", "fragment tekstu do wyszukania")],
        example="/inline geniusz",
    )
