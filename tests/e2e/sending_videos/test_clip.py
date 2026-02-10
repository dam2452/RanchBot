import pytest

import bot.responses.sending_videos.clip_handler_responses as msg
from tests.e2e.base_test import BaseTest


@pytest.mark.usefixtures("db_pool")
class TestClipHandler(BaseTest):
    @pytest.mark.asyncio
    async def test_clip_found(self):
        quote = "geniusz"
        self.assert_command_result_file_matches(
            self.send_command(f'/klip {quote}'),
            f"clip_{quote}.mp4",
        )

    @pytest.mark.asyncio
    async def test_clip_not_found(self):
        self.expect_command_result_contains(
            '/klip nieistniejący_cytat', [msg.get_no_segments_found_message()],
        )

    @pytest.mark.asyncio
    async def test_no_quote_provided(self):
        self.expect_command_result_contains(
            '/klip', [msg.get_no_quote_provided_message()],
        )
