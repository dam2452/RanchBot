from datetime import (
    date,
    timedelta,
)

import pytest

from bot.database.database_manager import DatabaseManager
from bot.database.response_keys import ResponseKey as RK
from bot.tests.base_test import BaseTest
from bot.tests.settings import settings as s


@pytest.mark.usefixtures("db_pool", "test_client", "auth_token")
class TestAddSubscriptionHandler(BaseTest):
    @pytest.mark.asyncio
    async def test_add_subscription_valid_user(self):
        user_id = 123456789
        days = 30

        await DatabaseManager.add_user(
            user_id=user_id,
            username="test_user",
            full_name="Test User",
            note=None,
            subscription_days=None,
        )

        expected_end_date = date.today() + timedelta(days=days)

        await self.expect_command_result_contains(
            'addsubscription',
            [await self.get_response(RK.SUBSCRIPTION_EXTENDED, [str(user_id), str(expected_end_date)])],
            args=[str(user_id), str(days)]
        )


    @pytest.mark.asyncio
    async def test_add_subscription_existing_admin(self):
        days = 60
        expected_end_date = date.today() + timedelta(days=days)

        await self.expect_command_result_contains(
            'addsubscription',
            [await self.get_response(RK.SUBSCRIPTION_EXTENDED, [str(s.DEFAULT_ADMIN), str(expected_end_date)])],
            args=[str(s.DEFAULT_ADMIN), str(days)]
        )


    
    @pytest.mark.asyncio
    async def test_add_subscription_nonexistent_user(self):
        user_id = 999999999
        days = 30

        await self.expect_command_result_contains(
            'addsubscription',
            [await self.get_response(RK.SUBSCRIPTION_ERROR)],
            args=[str(user_id), str(days)]
        )

    
    @pytest.mark.asyncio
    async def test_add_subscription_invalid_days_format(self):
        user_id = 123456789
        invalid_days = "trzydzieści"

        await self.expect_command_result_contains(
            'addsubscription',
            [await self.get_response(RK.NO_USER_ID_PROVIDED)],
            args=[str(user_id), str(invalid_days)],
        )

    
    @pytest.mark.asyncio
    async def test_add_subscription_invalid_user_id_format(self):
        user_id_invalid = "user123"
        days = 30

        await self.expect_command_result_contains(
            'addsubscription',
            [await self.get_response(RK.NO_USER_ID_PROVIDED)],
            args=[str(user_id_invalid), str(days)],
        )

    
    @pytest.mark.asyncio
    async def test_add_subscription_negative_days(self):
        user_id = 123456789
        negative_days = -30

        await self.expect_command_result_contains(
            'addsubscription',
            [await self.get_response(RK.NO_USER_ID_PROVIDED)],
            args=[str(user_id), str(negative_days)],
        )
