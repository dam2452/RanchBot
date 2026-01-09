import pytest

from bot.database.database_manager import DatabaseManager
from bot.database.models import UserProfile
from bot.responses.administration.list_whitelist_handler_responses import create_whitelist_response
from bot.tests.base_test import BaseTest
from bot.tests.settings import settings


@pytest.mark.usefixtures("db_pool", "test_client", "auth_token")
class TestListWhitelistCommand(BaseTest):
    @pytest.mark.asyncio
    async def test_list_whitelist_with_users(self):
        user1 = {
            "user_id": 123456,
            "username": "test_user1",
            "full_name": "Test User 1",
        }
        user2 = {
            "user_id": 789012,
            "username": "test_user2",
            "full_name": "Test User 2",
        }

        await DatabaseManager.add_user(
            user_id=user1["user_id"],
            username=user1["username"],
            full_name=user1["full_name"],
            note=None,
            subscription_days=None,
        )
        await DatabaseManager.add_user(
            user_id=user2["user_id"],
            username=user2["username"],
            full_name=user2["full_name"],
            note=None,
            subscription_days=None,
        )

        user_ids = settings.TEST_ADMINS.split(",")

        users = [
            UserProfile(
                user_id=user_ids[0],
                username="TestUser0",
                full_name="TestUser0",
                subscription_end=None,
                note=None,
            ),
            UserProfile(
                user_id=user_ids[1],
                username="TestUser1",
                full_name="TestUser1",
                subscription_end=None,
                note=None,
            ),
            UserProfile(
                user_id=user1["user_id"],
                username=user1["username"],
                full_name=user1["full_name"],
                subscription_end=None,
                note=None,
            ),
            UserProfile(
                user_id=user2["user_id"],
                username=user2["username"],
                full_name=user2["full_name"],
                subscription_end=None,
                note=None,
            ),
        ]
        self.expect_command_result_contains('/listwhitelist', [create_whitelist_response(users)])
