import pytest

import bot.responses.sending_videos.send_clip_handler_responses as msg
from tests.e2e.base_test import BaseTest


@pytest.mark.usefixtures("db_pool")
class TestSendClipHandler(BaseTest):
    @pytest.mark.asyncio
    async def test_send_clip_with_special_characters_in_name(self):
        clip_name = "klip@specjalny!"
        self.send_command('/klip geniusz')
        self.send_command(f'/zapisz {clip_name}')

        response = self.send_command(f'/wyslij {clip_name}')
        self.assert_command_result_file_matches(
            response, f'{clip_name}.mp4',
        )
