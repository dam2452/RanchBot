import pytest

from bot.database.database_manager import DatabaseManager
import bot.responses.administration.remove_subscription_handler_responses as msg
from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool", "test_client", "auth_token")
class TestRemoveSubscriptionHandler(BaseTest):

    @pytest.mark.asyncio
    async def test_remove_existing_subscription(self):
        user_id = 2015344951
        await DatabaseManager.add_user(
            user_id=user_id,
            username="test_user",
            full_name="Test User",
            note=None,
            subscription_days=30,
        )
        self.expect_command_result_contains(
            f'/removesubscription {user_id}',
            [msg.get_subscription_removed_message(str(user_id))],
        )

    @pytest.mark.asyncio
    async def test_remove_nonexistent_subscription(self):
        user_id = 987654321
        self.expect_command_result_contains(
            f'/removesubscription {user_id}',
            [msg.get_subscription_removed_message(str(user_id))],
        )

    @pytest.mark.asyncio
    async def test_remove_subscription_invalid_user_id_format(self):
        self.expect_command_result_contains(
            '/removesubscription user123',
            [msg.get_no_user_id_provided_message()],
        )

    @pytest.mark.asyncio
    async def test_remove_subscription_twice(self):
        user_id = 2015344951
        await DatabaseManager.add_user(
            user_id=user_id,
            username="test_user",
            full_name="Test User",
            note=None,
            subscription_days=30,
        )
        self.expect_command_result_contains(
            f'/removesubscription {user_id}',
            [msg.get_subscription_removed_message(str(user_id))],
        )
        self.expect_command_result_contains(
            f'/removesubscription {user_id}',
            [msg.get_subscription_removed_message(str(user_id))],
        )
