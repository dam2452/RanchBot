import pytest

import bot.responses.filter_command_messages as filter_msg
from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool")
class TestClipFilterHandler(BaseTest):

    @pytest.mark.asyncio
    async def test_clip_filter_no_active_filter(self):
        self.send_command('/filtr reset')
        response = self.send_command('/klipfiltr')
        self.assert_response_contains(response, [filter_msg.get_no_filter_set_message()])

    @pytest.mark.asyncio
    async def test_clip_filter_alias_kf_no_active_filter(self):
        self.send_command('/filtr reset')
        response = self.send_command('/kf')
        self.assert_response_contains(response, [filter_msg.get_no_filter_set_message()])

    @pytest.mark.asyncio
    async def test_clip_filter_with_active_filter(self):
        self.send_command('/filtr reset')
        self.send_command('/filtr sezon:1')
        response = self.send_command('/klipfiltr')
        self.assert_command_result_file_matches(response, "clip_filter_sezon1.mp4")

    @pytest.mark.asyncio
    async def test_clip_filter_with_quote(self):
        self.send_command('/filtr reset')
        self.send_command('/filtr sezon:1')
        response = self.send_command('/kf geniusz')
        self.assert_command_result_file_matches(response, "clip_filter_sezon1_geniusz.mp4")

    @pytest.mark.asyncio
    async def test_clip_filter_no_matching_segments(self):
        self.send_command('/filtr reset')
        self.send_command('/filtr sezon:99')
        response = self.send_command('/klipfiltr')
        self.assert_response_contains(response, [filter_msg.get_no_segments_match_active_filter_message()])
