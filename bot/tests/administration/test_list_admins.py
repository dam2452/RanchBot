import pytest

from bot.database.models import UserProfile
import bot.responses.administration.list_admins_handler_responses as msg
from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool", "test_client", "auth_token")
class TestListAdminsCommand(BaseTest):

    @pytest.mark.asyncio
    async def test_list_admins_with_admins(self):
        admins = [
            UserProfile(
                user_id=self.default_admin,
                username="TestUser0",
                full_name="TestUser0",
            ),
        ]

        self.expect_command_result_contains('/listadmins', [msg.format_admins_list(admins)])
