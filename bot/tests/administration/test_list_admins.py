import pytest

from bot.database.models import UserProfile
import bot.responses.administration.list_admins_handler_responses as msg
from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool", "test_client", "auth_token")
class TestListAdminsCommand(BaseTest):

    @pytest.mark.asyncio
    async def test_list_admins_with_admins(self):
        admin_user = await self.add_test_admin_user()

        admins = [
            UserProfile(
                user_id=admin_user["user_id"],
                username=admin_user["username"],
                full_name=admin_user["full_name"],
                subscription_end=None,
                note=None,
            ),
        ]

        self.expect_command_result_contains('/listadmins', [msg.format_admins_list(admins)])
