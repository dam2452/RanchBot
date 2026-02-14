import pytest

import bot.responses.sending_videos.adjust_video_clip_handler_responses as msg
from tests.e2e.base_test import BaseTest


@pytest.mark.usefixtures("db_pool")
class TestAdjustVideoClipHandler(BaseTest):
    @pytest.mark.asyncio
    async def test_adjust_clip_with_valid_params(self):
        video_name = "geniusz"
        adjust_params = "-5.5 1.5"
        adjusted_filename = f"adjusted_{video_name}_{adjust_params}.mp4"
        self.assert_command_result_file_matches(self.send_command(f"/klip {video_name}"), "clip_geniusz.mp4")

        self.assert_command_result_file_matches(self.send_command(f"/d {adjust_params}"), adjusted_filename)
        self.assert_command_result_file_matches(self.send_command(f"/ad {adjust_params}"), adjusted_filename)
