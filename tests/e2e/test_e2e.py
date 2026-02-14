import pytest

from bot.database import db
import bot.responses.not_sending_videos.my_clips_handler_responses as myclips_msg
import bot.responses.not_sending_videos.save_clip_handler_responses as save_clip_msg
from tests.e2e.base_test import BaseTest


@pytest.mark.usefixtures("db_pool")
class TestE2E(BaseTest):
    @pytest.mark.asyncio
    async def test_save_clip(self):
        clip_name = "traktor@#!$"
        self.send_command("/klip geniusz")
        self.expect_command_result_contains(
            f'/zapisz {clip_name}',
            [save_clip_msg.get_clip_saved_successfully_message(clip_name)],
        )
        clips = await db.get_saved_clips(self.default_admin)
        self.expect_command_result_contains(
            '/mojeklipy',
            [self.remove_n_lines(myclips_msg.format_myclips_response(clips, "TestUser0", "TestUser0", await self.get_season_info()), 4)],
        )

    @pytest.mark.asyncio
    async def test_transcription(self):
        response = self.send_command('/transkrypcja Nie szkoda panu tego pięknego gabinetu?')
        self.assert_message_hash_matches(response, expected_key="transcription_quote_gabinetu.message")

    @pytest.mark.asyncio
    async def test_inline_clip_handler(self):
        self.send_command("/szukaj piwo")
        self.send_command("/kompiluj 1 2 3")
        self.send_command("/zapisz piwo")

        response = self.send_command("/inline piwo")

        self.assert_command_result_file_matches(
            response, "inline_piwo.zip",
        )

    @pytest.mark.asyncio
    async def test_send_clip(self):
        clip_name = "klip@specjalny!"
        self.send_command('/klip geniusz')
        self.send_command(f'/zapisz {clip_name}')

        response = self.send_command(f'/wyslij {clip_name}')
        self.assert_command_result_file_matches(
            response, f'{clip_name}.mp4',
        )

    @pytest.mark.asyncio
    async def test_adjust_clip(self):
        video_name = "geniusz"
        adjust_params = "-5.5 1.5"
        adjusted_filename = f"adjusted_{video_name}_{adjust_params}.mp4"
        self.assert_command_result_file_matches(self.send_command(f"/klip {video_name}"), "clip_geniusz.mp4")

        self.assert_command_result_file_matches(self.send_command(f"/d {adjust_params}"), adjusted_filename)
        self.assert_command_result_file_matches(self.send_command(f"/ad {adjust_params}"), adjusted_filename)

    @pytest.mark.asyncio
    async def test_clip(self):
        quote = "geniusz"
        self.assert_command_result_file_matches(
            self.send_command(f'/klip {quote}'),
            f"clip_{quote}.mp4",
        )

    @pytest.mark.asyncio
    async def test_select_clip(self):
        quote = "geniusz"
        await self.expect_command_result_hash(
            f'/szukaj {quote}',
            expected_key=f"search_{quote}_results.message",
        )

        select_response = self.send_command('/wybierz 1')
        self.assert_command_result_file_matches(select_response, f'selected_{quote}_clip_1.mp4')

    @pytest.mark.asyncio
    async def test_compile_clips(self):
        message = self.send_command('/szukaj Anglii')
        self.assert_message_hash_matches(message, expected_key="search_anglii_results.message")

        response = self.send_command('/kompiluj wszystko')
        self.assert_command_result_file_matches(response, 'compile_anglii_all.mp4')
