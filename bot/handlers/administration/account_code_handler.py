from datetime import (
    datetime,
    timedelta,
    timezone,
)
import logging
from typing import List

from bot.adapters.rest.auth.auth_service import generate_linking_token
from bot.database.database_manager import DatabaseManager
from bot.handlers.bot_message_handler import BotMessageHandler
from bot.responses.administration.account_code_handler_responses import (
    get_already_has_credentials_message,
    get_code_generated_message,
)


class AccountCodeHandler(BotMessageHandler):
    def get_commands(self) -> List[str]:
        return ["kodkonta", "accountcode"]

    async def _do_handle(self) -> None:
        user_id = self._message.get_user_id()

        if await DatabaseManager.has_credentials(user_id):
            await self._reply(get_already_has_credentials_message())
            return

        token = generate_linking_token()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
        await DatabaseManager.store_verification_token(
            user_id=user_id,
            token=token,
            purpose="attach_credentials",
            expires_at=expires_at,
        )

        await self._reply(get_code_generated_message(token))
        await self._log_system_message(
            logging.INFO,
            f"Generated attach_credentials token for Telegram user {user_id}",
        )
