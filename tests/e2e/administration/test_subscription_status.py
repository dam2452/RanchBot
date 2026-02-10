from datetime import (
    date,
    timedelta,
)

import pytest

import bot.responses.administration.subscription_status_handler_responses as msg
from tests.e2e.base_test import BaseTest


@pytest.mark.usefixtures("db_pool", "test_client", "auth_token")
class TestSubscriptionStatusHandler(BaseTest):
    @pytest.mark.asyncio
    async def test_subscription_with_active_subscription(self):
        days = 30
        end_date = date.today() + timedelta(days=days)
        self.send_command(f'/addsubscription {self.default_admin} {days}')
        expected_response = msg.format_subscription_status_response(
            "TestUser0", end_date, days,
        )

        self.expect_command_result_contains('/subskrypcja', [expected_response])
        self.send_command(f'/removesubscription {self.default_admin}')

    @pytest.mark.asyncio
    async def test_subscription_without_subscription(self):
        self.send_command(f'/removesubscription {self.default_admin}')
        self.expect_command_result_contains(
            '/subskrypcja', [msg.get_no_subscription_message()],
        )

    @pytest.mark.asyncio
    async def test_subscription_with_expired_subscription(self):
        self.expect_command_result_contains(
            '/subskrypcja', [msg.get_no_subscription_message()],
        )

    @pytest.mark.asyncio
    async def test_subscription_long_duration(self):
        long_duration = 365 * 2
        end_date = date.today() + timedelta(days=long_duration)
        self.send_command(f'/addsubscription {self.default_admin} {long_duration}')
        expected_response = msg.format_subscription_status_response(
            "TestUser0", end_date, long_duration,
        )

        self.expect_command_result_contains('/subskrypcja', [expected_response])

    @pytest.mark.asyncio
    async def test_subscription_invalid_user(self):
        invalid_user_id = 99999
        response = self.send_command(f'/subskrypcja {invalid_user_id}')
        self.assert_response_contains(response, [msg.get_no_subscription_message()])
