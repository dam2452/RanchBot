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
