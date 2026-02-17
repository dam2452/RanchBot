import pytest

import bot.responses.sending_videos.snap_clip_handler_responses as msg
from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool")
class TestSnapClipHandler(BaseTest):

    @pytest.mark.asyncio
    async def test_snap_no_last_clip(self):
        self.expect_command_result_contains("/snap", [msg.get_no_last_clip_message()])

    @pytest.mark.asyncio
    async def test_snap_no_adjusted_times(self):
        video_name = "geniusz"
        self.send_command(f"/klip {video_name}")
        self.expect_command_result_contains("/snap", [msg.get_no_adjusted_times_message()])

    @pytest.mark.asyncio
    async def test_snap_already_snapped(self):
        video_name = "geniusz"
        self.send_command(f"/klip {video_name}")
        self.send_command("/d -1.5 1.5")
        self.send_command("/snap")
        second_snap = self.send_command("/snap")
        self.assert_response_contains(second_snap, [msg.get_already_snapped_message()])

    @pytest.mark.asyncio
    async def test_snap_success(self):
        video_name = "geniusz"
        self.send_command(f"/klip {video_name}")
        self.send_command("/d -1.5 1.5")
        response = self.send_command("/snap")
        self.assert_response_contains(response, ["✅ Klip wyrównany do cięć scen."])

    @pytest.mark.asyncio
    async def test_snap_alias_dopasuj(self):
        video_name = "geniusz"
        self.send_command(f"/klip {video_name}")
        self.send_command("/d -1.5 1.5")
        response = self.send_command("/dopasuj")
        self.assert_response_contains(response, ["✅ Klip wyrównany do cięć scen."])

    @pytest.mark.asyncio
    async def test_snap_alias_sp(self):
        video_name = "geniusz"
        self.send_command(f"/klip {video_name}")
        self.send_command("/d -1.5 1.5")
        response = self.send_command("/sp")
        self.assert_response_contains(response, ["✅ Klip wyrównany do cięć scen."])
