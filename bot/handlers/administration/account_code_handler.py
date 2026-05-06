from datetime import (
    datetime,
    timedelta,
    timezone,
)
import logging
from typing import List

from bot.adapters.rest.auth.auth_service import (
    generate_linking_token,
    generate_verification_code,
)
from bot.database.database_manager import DatabaseManager
from bot.handlers.bot_message_handler import BotMessageHandler
from bot.responses.administration.account_code_handler_responses import (
    get_code_generated_message,
    get_password_reset_code_message,
)


class AccountCodeHandler(BotMessageHandler):
    def get_commands(self) -> List[str]:
        return ["kodkonta", "accountcode"]

    async def _do_handle(self) -> None:
        user_id = self._message.get_user_id()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)

        if await DatabaseManager.has_credentials(user_id):
            code = generate_verification_code()
            await DatabaseManager.store_verification_token(
                user_id=user_id,
                token=code,
                purpose="password_reset",
                expires_at=expires_at,
            )
            await self._reply(get_password_reset_code_message(code))
            await self._log_system_message(
                logging.INFO,
                f"Generated password_reset code for Telegram user {user_id}",
            )
            return

        token = generate_linking_token()
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
