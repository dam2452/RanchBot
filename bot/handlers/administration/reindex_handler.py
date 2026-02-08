import logging
import time
from typing import List

from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.administration.reindex_handler_responses import (
    get_no_new_series_message,
    get_reindex_all_complete_message,
    get_reindex_all_new_complete_message,
    get_reindex_complete_message,
    get_reindex_error_message,
    get_reindex_progress_message,
    get_reindex_started_message,
    get_reindex_usage_message,
)
from bot.services.reindex.reindex_service import ReindexService


class ReindexHandler(BotMessageHandler):
    def __init__(self, message, responder, logger):
        super().__init__(message, responder, logger)
        self.reindex_service = ReindexService(logger)
        self.last_progress_time = 0
        self.progress_message = None

    def get_commands(self) -> List[str]:
        return ["reindeksuj", "reindex", "ridx"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [
            self.__check_argument_count,
            self.__check_target_valid,
        ]

    async def __check_argument_count(self) -> bool:
        return await self._validate_argument_count(
            self._message, 1, get_reindex_usage_message(),
        )

    async def __check_target_valid(self) -> bool:
        args = self._message.get_text().split()
        target = args[1]

        if target in {"all", "all-new"}:
            return True

        if not target.replace('_', '').replace('-', '').isalnum():
            await self.reply_error(get_reindex_usage_message())
            return False

        return True

    async def _do_handle(self) -> None:
        args = self._message.get_text().split()
        target = args[1]

        await self.reply(get_reindex_started_message(target))

        progress_callback = self.__create_progress_callback()

        try:
            if target == "all":
                results = await self.reindex_service.reindex_all(progress_callback)
                total_docs = sum(r.documents_indexed for r in results)
                total_eps = sum(r.episodes_processed for r in results)
                await self.reply(
                    get_reindex_all_complete_message(len(results), total_eps, total_docs),
                )
            elif target == "all-new":
                results = await self.reindex_service.reindex_all_new(progress_callback)
                if not results:
                    await self.reply(get_no_new_series_message())
                    return
                total_docs = sum(r.documents_indexed for r in results)
                total_eps = sum(r.episodes_processed for r in results)
                await self.reply(
                    get_reindex_all_new_complete_message(len(results), total_eps, total_docs),
                )
            else:
                result = await self.reindex_service.reindex_series(
                    target, progress_callback,
                )
                await self.reply(get_reindex_complete_message(result))

            await self._log_system_message(
                logging.INFO,
                f"Reindex complete for target: {target}",
            )
        except Exception as e:
            await self.reply_error(get_reindex_error_message(str(e)))
            self._logger.exception(f"Reindex failed: {e}")
            await self._log_system_message(
                logging.ERROR,
                f"Reindex failed: {e}",
            )
        finally:
            await self.reindex_service.close()

    def __create_progress_callback(self):
        async def callback(message: str, current: int, total: int):
            now = time.time()

            if now - self.last_progress_time < 1:
                return

            self.last_progress_time = now

            progress_text = get_reindex_progress_message(message, current, total)

            if hasattr(self._responder, 'edit_text') and self.progress_message:
                await self._responder.edit_text(self.progress_message, progress_text)
            else:
                self.progress_message = await self._responder.send_markdown(progress_text)

        return callback
