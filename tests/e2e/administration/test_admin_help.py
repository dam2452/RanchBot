import pytest

import bot.responses.administration.admin_help_handler_responses as msg
from tests.e2e.base_test import BaseTest


@pytest.mark.usefixtures("db_pool", "test_client", "auth_token")
class TestAdminHelpHandler(BaseTest):
    @pytest.mark.asyncio
    async def test_admin_help(self):
        self.expect_command_result_contains(
            'admin',
            [self.remove_n_lines(msg.get_admin_help_message(), 1)],
        )

    @pytest.mark.asyncio
    async def test_admin_shortcuts(self):
        self.expect_command_result_contains(
            'admin',
            [self.remove_n_lines(msg.get_admin_shortcuts_message(), 1)],
            args=['skroty'],
        )

    @pytest.mark.asyncio
    async def test_admin_invalid_command(self):
        self.expect_command_result_contains(
            'admin',
            [self.remove_n_lines(msg.get_admin_help_message(), 1)],
            args=['nieistniejace_polecenie'],
        )
