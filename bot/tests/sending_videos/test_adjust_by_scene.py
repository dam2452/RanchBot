import pytest

import bot.responses.sending_videos.adjust_video_clip_handler_responses as msg
from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool")
class TestAdjustBySceneHandler(BaseTest):

    @pytest.mark.asyncio
    async def test_sd_no_last_clip(self):
        self.expect_command_result_contains("/sd 1 1", [msg.get_no_quotes_selected_message()])

    @pytest.mark.asyncio
    async def test_sd_no_scene_cuts(self):
        video_name = "geniusz"
        self.send_command(f"/klip {video_name}")
        response = self.send_command("/sd 1 1")
        self.assert_command_result_file_matches(response, "sd_geniusz.mp4")

    @pytest.mark.asyncio
    async def test_sd_invalid_args(self):
        video_name = "geniusz"
        self.send_command(f"/klip {video_name}")
        self.expect_command_result_contains("/sd abc xyz", [msg.get_sd_invalid_args_message()])

    @pytest.mark.asyncio
    async def test_sd_success(self):
        video_name = "geniusz"
        self.send_command(f"/klip {video_name}")
        response = self.send_command("/sd 1 1")
        self.assert_command_result_file_matches(response, "sd_geniusz.mp4")

    @pytest.mark.asyncio
    async def test_sd_alias_sdostosuj(self):
        video_name = "geniusz"
        self.send_command(f"/klip {video_name}")
        response = self.send_command("/sdostosuj 1 1")
        self.assert_command_result_file_matches(response, "sd_sdostosuj_geniusz.mp4")

    @pytest.mark.asyncio
    async def test_sd_alias_sadjust(self):
        video_name = "geniusz"
        self.send_command(f"/klip {video_name}")
        response = self.send_command("/sadjust 1 1")
        self.assert_command_result_file_matches(response, "sd_sadjust_geniusz.mp4")
