import pytest

import bot.responses.administration.reindex_handler_responses as msg
from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool")
class TestReindexHandler(BaseTest):

    @pytest.mark.asyncio
    async def test_reindex_without_args(self):
        response = self.send_command('/reindex')
        self.assert_response_contains(response, [msg.get_reindex_usage_message()])
