import pytest

import bot.responses.administration.link_account_handler_responses as msg
from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool")
class TestLinkAccountHandler(BaseTest):

    @pytest.mark.asyncio
    async def test_link_no_args(self):
        response = self.send_command('/link')
        self.assert_response_contains(response, [msg.get_invalid_args_message()])

    @pytest.mark.asyncio
    async def test_link_invalid_code(self):
        response = self.send_command('/link nieprawidlowykod123')
        self.assert_response_contains(response, [msg.get_invalid_code_message()])

    @pytest.mark.asyncio
    async def test_link_already_linked(self):
        response = self.send_command('/link jakiskod')
        self.assert_response_contains(response, [msg.get_already_linked_message()])
