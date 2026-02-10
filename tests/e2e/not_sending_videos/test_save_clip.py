import pytest

from bot.database.database_manager import DatabaseManager
import bot.responses.not_sending_videos.my_clips_handler_responses as myclips_msg
import bot.responses.not_sending_videos.save_clip_handler_responses as msg
from bot.settings import settings as sb
from tests.e2e.base_test import BaseTest


@pytest.mark.usefixtures("db_pool")
class TestSaveClipHandler(BaseTest):

    @pytest.mark.asyncio
    async def test_save_clip_valid_name(self):
        clip_name = "traktor"
        self.send_command("/klip geniusz")
        self.expect_command_result_contains(
            f'/zapisz {clip_name}',
            [msg.get_clip_saved_successfully_message(clip_name)],
        )
        clips = await DatabaseManager.get_saved_clips(self.default_admin)
        self.expect_command_result_contains(
            '/mojeklipy',
            [self.remove_n_lines(myclips_msg.format_myclips_response(clips, "TestUser0", "TestUser0" , await self.get_season_info()), 4)],
        )

    @pytest.mark.asyncio
    async def test_save_clip_without_name(self):
        self.expect_command_result_contains(
            '/zapisz',
            [msg.get_clip_name_not_provided_message()],
        )

    @pytest.mark.asyncio
    async def test_save_clip_special_characters_in_name(self):
        clip_name = "traktor@#!$"
        self.send_command("/klip geniusz")
        self.expect_command_result_contains(
            f'/zapisz {clip_name}',
            [msg.get_clip_saved_successfully_message(clip_name)],
        )
        clips = await DatabaseManager.get_saved_clips(self.default_admin)
        self.expect_command_result_contains(
            '/mojeklipy',
            [self.remove_n_lines(myclips_msg.format_myclips_response(clips, "TestUser0", "TestUser0", await self.get_season_info()), 4)],
        )

    @pytest.mark.asyncio
    async def test_save_clip_duplicate_name(self):
        clip_name = "traktor"
        self.send_command("/klip geniusz")
        self.expect_command_result_contains(
            f'/zapisz {clip_name}',
            [msg.get_clip_saved_successfully_message(clip_name)],
        )
        self.expect_command_result_contains(
            f'/zapisz {clip_name}',
            [msg.get_clip_name_exists_message(clip_name)],
        )

    @pytest.mark.asyncio
    async def test_save_clip_no_segment_selected(self):
        response = self.send_command('/zapisz klip_bez_segmentu')
        self.assert_response_contains(
            response,
            [msg.get_no_segment_selected_message()],
        )

    @pytest.mark.asyncio
    async def test_save_clip_name_length_exceeded(self):
        long_name = "a" * (sb.MAX_CLIP_NAME_LENGTH + 1)
        response = self.send_command(f'/zapisz {long_name}')
        self.assert_response_contains(
            response,
            [msg.get_clip_name_length_exceeded_message()],
        )
