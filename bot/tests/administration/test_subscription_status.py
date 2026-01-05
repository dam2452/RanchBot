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

    async def test_subscription_with_active_subscription(self):
        days = 30
        end_date = date.today() + timedelta(days=days)
        self.send_command(f'/addsubscription {s.DEFAULT_ADMIN} {days}')
        expected_response = await self.get_response(
            RK.SUBSCRIPTION_STATUS,[
                str(s.TESTER_USERNAME), str(end_date), str(days),
            ],
        )

        await self.expect_command_result_contains('/subskrypcja', [expected_response])
        self.send_command(f'/removesubscription {s.DEFAULT_ADMIN}')

    async def test_subscription_without_subscription(self):
        await self.add_test_admin_user()
        self.send_command(f'/removesubscription {s.DEFAULT_ADMIN}')
        await self.expect_command_result_contains(
            '/subskrypcja', [await self.get_response(RK.NO_SUBSCRIPTION)],
        )

    async def test_subscription_with_expired_subscription(self):
        await self.expect_command_result_contains(
            '/subskrypcja', [await self.get_response(RK.NO_SUBSCRIPTION)],
        )

    async def test_subscription_long_duration(self):
        await self.add_test_admin_user()
        long_duration = 365 * 2
        end_date = date.today() + timedelta(days=long_duration)
        self.send_command(f'/addsubscription {s.DEFAULT_ADMIN} {long_duration}')
        expected_response = await self.get_response(
            RK.SUBSCRIPTION_STATUS,[
                str(s.TESTER_USERNAME), str(end_date), str(long_duration),
            ],
        )

        await self.expect_command_result_contains('/subskrypcja', [expected_response])

    async def test_subscription_invalid_user(self):
        invalid_user_id = 99999
        response = self.send_command(f'/subskrypcja {invalid_user_id}')
        await self.assert_response_contains(response, [await self.get_response(RK.NO_SUBSCRIPTION)])
