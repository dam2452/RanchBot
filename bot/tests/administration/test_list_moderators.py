import pytest

from bot.database.database_manager import DatabaseManager
from bot.database.models import UserProfile
from bot.responses.administration.list_moderators_handler_responses import (
    format_moderators_list,
    get_no_moderators_found_message,
)
from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool", "test_client", "auth_token")
class TestListModeratorsCommand(BaseTest):
    @pytest.mark.asyncio
    async def test_list_moderators_with_moderators(self):
        moderators = [
            {
                "user_id": 123456,
                "username": "moderator1",
                "full_name": "Moderator One",
                "note": "Test note",
                "subscription_end": None,
            },
            {
                "user_id": 789012,
                "username": "moderator2",
                "full_name": "Moderator Two",
                "note": "Another test note",
                "subscription_end": None,
            },
        ]

        for user in moderators:
            await self.get_response(
                user_id=user["user_id"],
                username=user["username"],
                full_name=user["full_name"],
                note=user["note"],
                subscription_days=None,
            )
            await DatabaseManager.set_user_as_moderator(user_id=user["user_id"])

        user_profiles = [
            UserProfile(
                user_id=user["user_id"],
                username=user["username"],
                full_name=user["full_name"],
                note=user["note"],
                subscription_end=user["subscription_end"],
            )
            for user in moderators
        ]

        await self.expect_command_result_contains(
            '/listmoderators', [format_moderators_list(user_profiles)],
        )

    async def test_list_moderators_empty(self):
        await self.expect_command_result_contains(
            '/listmoderators', [get_no_moderators_found_message()],
        )
