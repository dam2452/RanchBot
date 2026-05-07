import pytest

import bot.responses.sending_videos.keyframe_handler_responses as msg
from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool")
class TestKeyframeHandler(BaseTest):

    @pytest.mark.asyncio
    async def test_keyframe_no_previous_search(self):
        response = self.send_command('/klatka')
        self.assert_response_contains(response, [msg.get_no_last_clip_message()])

    @pytest.mark.asyncio
    async def test_keyframe_default_frame(self):
        self.send_command('/klip geniusz')
        response = self.send_command('/klatka')
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_keyframe_with_result_index(self):
        self.send_command('/szukaj geniusz')
        response = self.send_command('/klatka 1')
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_keyframe_with_result_and_frame(self):
        self.send_command('/szukaj geniusz')
        response = self.send_command('/klatka 1 0')
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_keyframe_invalid_frame_selector(self):
        self.send_command('/szukaj geniusz')
        response = self.send_command('/klatka abc')
        self.assert_response_contains(response, [msg.get_invalid_frame_selector_message()])

    @pytest.mark.asyncio
    async def test_keyframe_invalid_result_index(self):
        self.send_command('/szukaj geniusz')
        response = self.send_command('/klatka abc 0')
        self.assert_response_contains(response, [msg.get_invalid_result_index_message()])

    @pytest.mark.asyncio
    async def test_keyframe_result_index_out_of_range(self):
        self.send_command('/szukaj geniusz')
        response = self.send_command('/klatka 999 0')
        self.assert_response_contains(response, [msg.get_invalid_result_index_message()])

    @pytest.mark.asyncio
    async def test_keyframe_alias_frame(self):
        self.send_command('/klip geniusz')
        response = self.send_command('/frame')
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_keyframe_alias_kl(self):
        self.send_command('/klip geniusz')
        response = self.send_command('/kl')
        assert response.status_code == 200
