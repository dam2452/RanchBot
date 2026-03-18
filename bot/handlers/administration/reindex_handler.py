import logging
import time
from typing import List

from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.administration.reindex_handler_responses import (
    get_delete_complete_message,
    get_delete_started_message,
    get_no_new_series_message,
    get_no_target_provided_message,
    get_reindex_all_complete_message,
    get_reindex_all_new_complete_message,
    get_reindex_complete_message,
    get_reindex_error_message,
    get_reindex_progress_message,
    get_reindex_started_message,
)
from bot.services.reindex.reindex_service import ReindexService


class ReindexHandler(BotMessageHandler):
    def __init__(self, message, responder, logger):
        super().__init__(message, responder, logger)
        self._last_progress_time = 0
        self._progress_message = None

    def get_commands(self) -> List[str]:
        return ["reindeksuj", "reindex", "ridx"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [
            self.__check_argument_count,
            self.__check_target_valid,
        ]

    def _get_usage_message(self) -> str:
        return get_no_target_provided_message()

    async def __check_argument_count(self) -> bool:
        args = self._message.get_text().split()
        if len(args) < 2:
            return await self._validate_argument_count(self._message, 1)
        if args[1] == "delete":
            return await self._validate_argument_count(self._message, 2)
        return await self._validate_argument_count(self._message, 1)

    async def __check_target_valid(self) -> bool:
        args = self._message.get_text().split()
        target = args[1]

        if target in {"all", "all-new"}:
            return True

        if target == "delete":
            series_name = args[2] if len(args) > 2 else ""
            if not series_name.replace('_', '').replace('-', '').isalnum():
                await self._reply_error(self._get_usage_message())
                return False
            return True

        if not target.replace('_', '').replace('-', '').isalnum():
            await self._reply_error(self._get_usage_message())
            return False

        return True

    async def _do_handle(self) -> None:
        args = self._message.get_text().split()
        target = args[1]

        progress_callback = self.__create_progress_callback()

        async with ReindexService(self._logger) as service:
            try:
                if target == "delete":
                    series_name = args[2]
                    await self._reply(get_delete_started_message(series_name))
                    deleted = await service.delete_series(series_name)
                    await self._reply(get_delete_complete_message(series_name, deleted))
                    await self._log_system_message(
                        logging.INFO, f"Deleted series indices: {series_name}",
                    )
                elif target == "all":
                    await self._reply(get_reindex_started_message(target))
                    results = await service.reindex_all(progress_callback)
                    total_docs = sum(r.documents_indexed for r in results)
                    total_eps = sum(r.episodes_processed for r in results)
                    await self._reply(
                        get_reindex_all_complete_message(len(results), total_eps, total_docs),
                    )
                    await self._log_system_message(
                        logging.INFO, f"Reindex complete for target: {target}",
                    )
                elif target == "all-new":
                    await self._reply(get_reindex_started_message(target))
                    results = await service.reindex_all_new(progress_callback)
                    if not results:
                        await self._reply(get_no_new_series_message())
                        return
                    total_docs = sum(r.documents_indexed for r in results)
                    total_eps = sum(r.episodes_processed for r in results)
                    await self._reply(
                        get_reindex_all_new_complete_message(len(results), total_eps, total_docs),
                    )
                    await self._log_system_message(
                        logging.INFO, f"Reindex complete for target: {target}",
                    )
                else:
                    await self._reply(get_reindex_started_message(target))
                    result = await service.reindex_series(target, progress_callback)
                    await self._reply(get_reindex_complete_message(result))
                    await self._log_system_message(
                        logging.INFO, f"Reindex complete for target: {target}",
                    )
            except Exception as e:
                await self._reply_error(get_reindex_error_message(str(e)))

    def __create_progress_callback(self):
        async def callback(message: str, current: int, total: int):
            now = time.time()

            if now - self._last_progress_time < 1:
                return

            self._last_progress_time = now

            progress_text = get_reindex_progress_message(message, current, total)

            if hasattr(self._responder, 'edit_text') and self._progress_message:
                await self._responder.edit_text(self._progress_message, progress_text)
            else:
                self._progress_message = await self._responder.send_markdown(progress_text)

        return callback
