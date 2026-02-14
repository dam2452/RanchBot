import pytest

import bot.responses.sending_videos.compile_clips_handler_responses as msg
from tests.e2e.base_test import BaseTest


@pytest.mark.usefixtures("db_pool")
class TestCompileClipsHandler(BaseTest):
    @pytest.mark.asyncio
    async def test_compile_all_clips(self):
        message = self.send_command(f'/szukaj Anglii')
        self.assert_message_hash_matches(message, expected_key="search_anglii_results.message")

        response = self.send_command('/kompiluj wszystko')
        self.assert_command_result_file_matches(response, 'compile_anglii_all.mp4')
