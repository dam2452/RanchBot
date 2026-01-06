import pytest

from bot.database.database_manager import DatabaseManager
from bot.database.response_keys import ResponseKey as RK
import bot.responses.not_sending_videos.my_clips_handler_responses as msg
from bot.tests.base_test import BaseTest
from bot.tests.settings import settings as s


@pytest.mark.usefixtures("db_pool")
class TestMyClipsHandler(BaseTest):
    @pytest.mark.asyncio
    async def test_myclips_no_clips(self):
        response = self.send_command('mojeklipy')
        self.assert_response_contains(response, [await self.get_response(RK.NO_SAVED_CLIPS)])

    @pytest.mark.asyncio
    async def test_myclips_with_regular_clips(self):
        self.send_command('klip geniusz')
        self.send_command('zapisz pierwszy_klip')

        clips = await DatabaseManager.get_saved_clips(s.DEFAULT_ADMIN)
        response = self.remove_n_lines(await msg.format_myclips_response(clips, s.TESTER_USERNAME, s.ADMIN_FULL_NAME, await self.get_season_info()), 4)
        self.expect_command_result_contains('mojeklipy', [response])

    @pytest.mark.asyncio
    async def test_myclips_with_compilation(self):
        self.send_command('sz geniusz')
        self.send_command('kom 1-3')
        self.send_command('zapisz klip_kompilacja')

        clips = await DatabaseManager.get_saved_clips(s.DEFAULT_ADMIN)
        for clip in clips:
            clip.is_compilation = True
        response = self.remove_n_lines(await msg.format_myclips_response(clips, s.ADMIN_USERNAME, s.ADMIN_FULL_NAME, await self.get_season_info()), 4)
        self.expect_command_result_contains('mojeklipy', [response])

    @pytest.mark.asyncio
    async def test_myclips_with_long_names(self):
        long_name = "klip_" + "g" * 35
        self.send_command('klip geniusz')
        self.send_command(f'zapisz {long_name}')

        clips = await DatabaseManager.get_saved_clips(s.DEFAULT_ADMIN)
        response = self.remove_n_lines(await msg.format_myclips_response(clips, s.ADMIN_USERNAME, s.ADMIN_FULL_NAME, await self.get_season_info()), 4)
        self.expect_command_result_contains('mojeklipy', [response])

    @pytest.mark.asyncio
    async def test_myclips_with_special_characters(self):
        special_name = "klip_!@#$%^&*()"
        self.send_command('klip geniusz')
        self.send_command(f'zapisz {special_name}')

        clips = await DatabaseManager.get_saved_clips(s.DEFAULT_ADMIN)
        response = self.remove_n_lines(await msg.format_myclips_response(clips, s.ADMIN_USERNAME, s.ADMIN_FULL_NAME, await self.get_season_info()), 4)
        self.expect_command_result_contains('mojeklipy', [response])

    @pytest.mark.asyncio
    async def test_myclips_empty_durations(self):
        self.send_command('klip geniusz')
        self.send_command('zapisz klip_bez_czasu')

        clips = await DatabaseManager.get_saved_clips(s.DEFAULT_ADMIN)
        for clip in clips:
            clip.duration = None
        response = self.remove_n_lines(await msg.format_myclips_response(clips, s.ADMIN_USERNAME, s.ADMIN_FULL_NAME, await self.get_season_info()), 5)
        self.expect_command_result_contains('mojeklipy', [response])
