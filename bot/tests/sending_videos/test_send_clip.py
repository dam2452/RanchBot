import pytest

from bot.database.response_keys import ResponseKey as RK
from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool")
class TestSendClipHandler(BaseTest):

    @pytest.mark.asyncio
    async def test_send_existing_clip_by_number(self):
        clip_name = "klip1"
        self.send_command('/klip geniusz')
        self.send_command(f'/zapisz {clip_name}')

        response = self.send_command('/wyslij 1')
        self.assert_command_result_file_matches(
            response, f'{clip_name}.mp4',
        )

    @pytest.mark.asyncio
    async def test_send_existing_clip_by_name(self):
        clip_name = "klip_geniusz"
        self.send_command('/klip geniusz')
        self.send_command(f'/zapisz {clip_name}')

        response = self.send_command(f'/wyslij {clip_name}')
        self.assert_command_result_file_matches(
            response, f'{clip_name}.mp4',
        )

    @pytest.mark.asyncio
    async def test_send_nonexistent_clip(self):
        clip_number = 1
        response = self.send_command(f'/wyslij {clip_number}')
        self.assert_response_contains(
            response, [await self.get_response(RK.CLIP_NOT_FOUND_NUMBER, [str(clip_number)])],
        )

    @pytest.mark.asyncio
    async def test_send_clip_with_special_characters_in_name(self):
        clip_name = "klip@specjalny!"
        self.send_command('/klip geniusz')
        self.send_command(f'/zapisz {clip_name}')

        response = self.send_command(f'/wyslij {clip_name}')
        self.assert_command_result_file_matches(
            response, f'{clip_name}.mp4',
        )
