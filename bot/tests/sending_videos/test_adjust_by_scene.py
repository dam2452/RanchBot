import pytest

import bot.responses.sending_videos.adjust_video_clip_handler_responses as msg
from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool")
class TestAdjustBySceneHandler(BaseTest):

    @pytest.mark.asyncio
    async def test_ds_no_last_clip(self):
        self.expect_command_result_contains("/ds 1 1", [msg.get_no_quotes_selected_message()])

    @pytest.mark.asyncio
    async def test_ds_no_scene_cuts(self):
        video_name = "geniusz"
        self.send_command(f"/klip {video_name}")
        self.expect_command_result_contains("/ds 1 1", [msg.get_ds_no_scene_cuts_message()])

    @pytest.mark.asyncio
    async def test_ds_invalid_args(self):
        video_name = "geniusz"
        self.send_command(f"/klip {video_name}")
        self.expect_command_result_contains("/ds abc xyz", [msg.get_ds_invalid_args_message()])

    @pytest.mark.asyncio
    async def test_ds_success(self):
        video_name = "geniusz"
        self.send_command(f"/klip {video_name}")
        response = self.send_command("/ds 1 1")
        self.assert_command_result_file_matches(response, "ds_geniusz.mp4")

    @pytest.mark.asyncio
    async def test_ds_alias_sdostosuj(self):
        video_name = "geniusz"
        self.send_command(f"/klip {video_name}")
        response = self.send_command("/sdostosuj 1 1")
        self.assert_command_result_file_matches(response, "ds_sdostosuj_geniusz.mp4")

    @pytest.mark.asyncio
    async def test_ds_alias_sadjust(self):
        video_name = "geniusz"
        self.send_command(f"/klip {video_name}")
        response = self.send_command("/sadjust 1 1")
        self.assert_command_result_file_matches(response, "ds_sadjust_geniusz.mp4")
