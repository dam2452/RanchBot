import pytest

import bot.responses.sending_videos.saved_clip_thumbnail_handler_responses as msg
from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool")
class TestSavedClipThumbnailHandler(BaseTest):

    @pytest.mark.asyncio
    async def test_saved_clip_thumbnail_no_args(self):
        response = self.send_command('/klatkaklipu')
        self.assert_response_contains(response, [msg.get_no_clip_identifier_provided_message()])

    @pytest.mark.asyncio
    async def test_saved_clip_thumbnail_alias_kk_no_args(self):
        response = self.send_command('/kk')
        self.assert_response_contains(response, [msg.get_no_clip_identifier_provided_message()])

    @pytest.mark.asyncio
    async def test_saved_clip_thumbnail_clip_not_found(self):
        response = self.send_command('/kk nieistniejacy')
        self.assert_response_contains(response, [msg.get_clip_not_found_message("nieistniejacy")])

    @pytest.mark.asyncio
    async def test_saved_clip_thumbnail_clip_not_found_by_index(self):
        response = self.send_command('/kk 1')
        self.assert_response_contains(response, [msg.get_clip_not_found_message("1")])

    @pytest.mark.asyncio
    async def test_saved_clip_thumbnail_by_name(self):
        clip_name = "klip_thumbnail"
        self.send_command('/klip geniusz')
        self.send_command(f'/zapisz {clip_name}')
        response = self.send_command(f'/kk {clip_name}')
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_saved_clip_thumbnail_by_index(self):
        clip_name = "klip_thumbnail_idx"
        self.send_command('/klip geniusz')
        self.send_command(f'/zapisz {clip_name}')
        response = self.send_command('/kk 1')
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_saved_clip_thumbnail_invalid_frame_selector(self):
        clip_name = "klip_thumbnail_fs"
        self.send_command('/klip geniusz')
        self.send_command(f'/zapisz {clip_name}')
        response = self.send_command(f'/kk {clip_name} abc')
        self.assert_response_contains(response, [msg.get_invalid_frame_selector_message()])
