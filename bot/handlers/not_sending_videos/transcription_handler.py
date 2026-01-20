import logging
import math
from typing import List

from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.bot_message_handler_responses import (
    get_log_no_segments_found_message,
    get_no_segments_found_message,
)
from bot.responses.not_sending_videos.transcription_handler_responses import (
    get_log_transcription_response_sent_message,
    get_no_quote_provided_message,
    get_transcription_response,
)
from bot.search.transcription_finder import TranscriptionFinder


class TranscriptionHandler(BotMessageHandler):
    def get_commands(self) -> List[str]:
        return ["transkrypcja", "transcription", "t"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [self.__check_argument_count]

    async def __check_argument_count(self) -> bool:
        return await self._validate_argument_count(self._message, 1, get_no_quote_provided_message(), math.inf)

    async def _do_handle(self) -> None:
        args = self._message.get_text().split()
        quote = " ".join(args[1:])

        result = await TranscriptionFinder.find_segment_with_context(quote, self._logger, context_size=15)

        if not result:
            return await self.__reply_no_segments_found(quote)

        await self.reply(
            get_transcription_response(quote, result),
            data={
                "quote": quote,
                "segment": result,
            },
        )

        return await self._log_system_message(
            logging.INFO,
            get_log_transcription_response_sent_message(quote, self._message.get_username()),
        )

    async def __reply_no_segments_found(self, quote: str) -> None:
        await self.reply_error(get_no_segments_found_message(quote))
        await self._log_system_message(logging.INFO, get_log_no_segments_found_message(quote))
