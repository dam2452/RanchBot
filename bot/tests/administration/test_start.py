import pytest

from bot.database.response_keys import ResponseKey as RK
from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool", "test_client", "auth_token")
class TestStartHandler(BaseTest):

    @pytest.mark.quick
    def test_start_base_command(self):
        self.expect_command_result_contains('/start', [self.remove_n_lines(self.get_response(RK.BASIC_MESSAGE),5)])

    @pytest.mark.quick
    def test_start_invalid_command(self):
        self.expect_command_result_contains(
            '/start', [self.remove_n_lines(self.get_response(RK.INVALID_COMMAND_MESSAGE),5)],
            args=['nieistniejace_polecenie']
        )

    def test_start_list_command(self):
        self.expect_command_result_contains('/start', [self.remove_n_lines(self.get_response(RK.LIST_MESSAGE),5)], args=['lista'])

    def test_start_search_section(self):
        self.expect_command_result_contains('/start', [self.remove_n_lines(self.get_response(RK.SEARCH_MESSAGE),5)], args=['wyszukiwanie'])

    def test_start_edit_section(self):
        self.expect_command_result_contains('/start', [self.remove_n_lines(self.get_response(RK.EDIT_MESSAGE),5)], args=['edycja'])

    def test_start_management_section(self):
        self.expect_command_result_contains('/start', [self.remove_n_lines(self.get_response(RK.MANAGEMENT_MESSAGE),5)], args=['zarzadzanie'])

    def test_start_reporting_section(self):
        self.expect_command_result_contains('/start', [self.remove_n_lines(self.get_response(RK.REPORTING_MESSAGE),5)], args=['raportowanie'])

    def test_start_subscriptions_section(self):
        self.expect_command_result_contains('/start', [self.remove_n_lines(self.get_response(RK.SUBSCRIPTIONS_MESSAGE),5)], args=['subskrypcje'])

    def test_start_all_commands(self):
        self.expect_command_result_contains('/start', [self.remove_n_lines(self.get_response(RK.ALL_MESSAGE),5)], args=['wszystko'])

    def test_start_shortcuts(self):
        self.expect_command_result_contains('/start', [self.remove_n_lines(self.get_response(RK.SHORTCUTS_MESSAGE),5)], args=['skroty'])
