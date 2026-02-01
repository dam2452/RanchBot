import pytest

import bot.responses.administration.start_handler_responses as msg
from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool", "test_client", "auth_token")
class TestStartHandler(BaseTest):

    @pytest.mark.asyncio
    async def test_start_base_command(self):
        self.expect_command_result_contains('/start', [self.remove_n_lines(msg.get_basic_message(), 5)])

    @pytest.mark.asyncio
    async def test_start_invalid_command(self):
        self.expect_command_result_contains(
            '/start', [self.remove_n_lines(msg.get_invalid_command_message(), 5)],
            args=['nieistniejace_polecenie'],
        )

    @pytest.mark.asyncio
    async def test_start_list_command(self):
        self.expect_command_result_contains('/start', [self.remove_n_lines(msg.get_list_message(), 5)], args=['lista'])

    @pytest.mark.asyncio
    async def test_start_search_section(self):
        self.expect_command_result_contains('/start', [self.remove_n_lines(msg.get_search_message(), 5)], args=['wyszukiwanie'])

    @pytest.mark.asyncio
    async def test_start_edit_section(self):
        self.expect_command_result_contains('/start', [self.remove_n_lines(msg.get_edit_message(), 5)], args=['edycja'])

    @pytest.mark.asyncio
    async def test_start_management_section(self):
        self.expect_command_result_contains('/start', [self.remove_n_lines(msg.get_menagement_message(), 5)], args=['zarzadzanie'])

    @pytest.mark.asyncio
    async def test_start_reporting_section(self):
        self.expect_command_result_contains('/start', [self.remove_n_lines(msg.get_reporting_message(), 5)], args=['raportowanie'])

    @pytest.mark.asyncio
    async def test_start_subscriptions_section(self):
        self.expect_command_result_contains('/start', [self.remove_n_lines(msg.get_subscriptions_message(), 5)], args=['subskrypcje'])

    @pytest.mark.asyncio
    async def test_start_all_commands(self):
        self.expect_command_result_contains('/start', [self.remove_n_lines(msg.get_all_message(), 5)], args=['wszystko'])

    @pytest.mark.asyncio
    async def test_start_shortcuts(self):
        self.expect_command_result_contains('/start', [self.remove_n_lines(msg.get_shortcuts_message(), 5)], args=['skroty'])
