import pytest

import bot.responses.sending_videos.save_clip_by_index_handler_responses as msg
from bot.settings import settings as sb
from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool")
class TestSaveClipByIndexHandler(BaseTest):

    @pytest.mark.asyncio
    async def test_save_by_index_no_args(self):
        response = self.send_command('/zapisznumer')
        self.assert_response_contains(response, [msg.get_usage_message()])

    @pytest.mark.asyncio
    async def test_save_by_index_alias_zn_no_args(self):
        response = self.send_command('/zn')
        self.assert_response_contains(response, [msg.get_usage_message()])

    @pytest.mark.asyncio
    async def test_save_by_index_no_previous_search(self):
        response = self.send_command('/zn 1 testclip')
        self.assert_response_contains(response, [msg.get_no_previous_search_message()])

    @pytest.mark.asyncio
    async def test_save_by_index_invalid_segment_number(self):
        self.send_command('/szukaj geniusz')
        response = self.send_command('/zn 999 testclip')
        self.assert_response_contains(response, [msg.get_invalid_segment_number_message(999)])

    @pytest.mark.asyncio
    async def test_save_by_index_numeric_clip_name(self):
        self.send_command('/szukaj geniusz')
        response = self.send_command('/zn 1 123')
        self.assert_response_contains(response, [msg.get_clip_name_numeric_message()])

    @pytest.mark.asyncio
    async def test_save_by_index_name_length_exceeded(self):
        self.send_command('/szukaj geniusz')
        long_name = "a" * (sb.MAX_CLIP_NAME_LENGTH + 1)
        response = self.send_command(f'/zn 1 {long_name}')
        self.assert_response_contains(response, [msg.get_clip_name_length_exceeded_message()])

    @pytest.mark.asyncio
    async def test_save_by_index_valid(self):
        clip_name = "testindex"
        self.send_command('/szukaj geniusz')
        response = self.send_command(f'/zn 1 {clip_name}')
        self.assert_response_contains(response, [msg.get_clip_saved_successfully_message(clip_name)])

    @pytest.mark.asyncio
    async def test_save_by_index_duplicate_name(self):
        clip_name = "testduplikat"
        self.send_command('/szukaj geniusz')
        self.send_command(f'/zn 1 {clip_name}')
        response = self.send_command(f'/zn 1 {clip_name}')
        self.assert_response_contains(response, [msg.get_clip_name_exists_message(clip_name)])

    @pytest.mark.asyncio
    async def test_save_by_index_with_adjustments(self):
        clip_name = "testadj"
        self.send_command('/szukaj geniusz')
        response = self.send_command(f'/zn 1 -1 1 {clip_name}')
        self.assert_response_contains(response, [msg.get_clip_saved_successfully_message(clip_name)])

    @pytest.mark.asyncio
    async def test_save_by_index_invalid_adjust_format(self):
        self.send_command('/szukaj geniusz')
        response = self.send_command('/zn 1 abc testclip')
        self.assert_response_contains(response, [msg.get_invalid_adjust_format_message()])
