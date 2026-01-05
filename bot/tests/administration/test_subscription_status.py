from datetime import (
    date,
    timedelta,
)

import pytest

from bot.database.response_keys import ResponseKey as RK
from bot.tests.base_test import BaseTest
from bot.tests.settings import settings as s


@pytest.mark.usefixtures("db_pool", "test_client", "auth_token")
class TestSubscriptionStatusHandler(BaseTest):
    @pytest.mark.asyncio
    async def test_subscription_with_active_subscription(self):
        days = 30
        end_date = date.today() + timedelta(days=days)
        await self.send_command(f'/addsubscription {s.DEFAULT_ADMIN} {days}')
        expected_response = await self.get_response(
            RK.SUBSCRIPTION_STATUS,[
                str(s.TESTER_USERNAME), str(end_date), str(days),
            ],
        )

        await self.expect_command_result_contains('/subskrypcja', [expected_response])
        await self.send_command(f'/removesubscription {s.DEFAULT_ADMIN}')

    @pytest.mark.asyncio
    async def test_subscription_without_subscription(self):
        await self.add_test_admin_user()
        await self.send_command(f'/removesubscription {s.DEFAULT_ADMIN}')
        await self.expect_command_result_contains(
            '/subskrypcja', [await self.get_response(RK.NO_SUBSCRIPTION)],
        )

    @pytest.mark.asyncio
    async def test_subscription_with_expired_subscription(self):
        await self.expect_command_result_contains(
            '/subskrypcja', [await self.get_response(RK.NO_SUBSCRIPTION)],
        )

    @pytest.mark.asyncio
    async def test_subscription_long_duration(self):
        await self.add_test_admin_user()
        long_duration = 365 * 2
        end_date = date.today() + timedelta(days=long_duration)
        await self.send_command(f'/addsubscription {s.DEFAULT_ADMIN} {long_duration}')
        expected_response = await self.get_response(
            RK.SUBSCRIPTION_STATUS,[
                str(s.TESTER_USERNAME), str(end_date), str(long_duration),
            ],
        )

        await self.expect_command_result_contains('/subskrypcja', [expected_response])

    @pytest.mark.asyncio
    async def test_subscription_invalid_user(self):
        invalid_user_id = 99999
        response = await self.send_command(f'/subskrypcja {invalid_user_id}')
        await self.assert_response_contains(response, [await self.get_response(RK.NO_SUBSCRIPTION)])
