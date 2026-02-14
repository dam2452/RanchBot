import pytest

import bot.responses.sending_videos.select_clip_handler_responses as msg
from tests.e2e.base_test import BaseTest


@pytest.mark.usefixtures("db_pool")
class TestSelectClipHandler(BaseTest):
    @pytest.mark.asyncio
    async def test_select_valid_segment(self):
        quote = "geniusz"
        await self.expect_command_result_hash(
            f'/szukaj {quote}',
            expected_key=f"search_{quote}_results.message",
        )

        select_response = self.send_command('/wybierz 1')
        self.assert_command_result_file_matches(select_response, f'selected_{quote}_clip_1.mp4')
