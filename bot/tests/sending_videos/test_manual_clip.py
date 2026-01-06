import pytest

from bot.database.response_keys import ResponseKey as RK
from bot.tests.base_test import BaseTest


@pytest.mark.skip(reason="TODO FIXME")
@pytest.mark.usefixtures("db_pool")
class TestManualClipHandler(BaseTest):

    @pytest.mark.asyncio
    async def test_cut_clip_valid_range(self):
        episode = "S07E06"
        start_time = "36:47.50"
        end_time = "36:49.00"
        expected_file = f"cut_{episode}_{start_time}_{end_time}.mp4"

        command = f"/wytnij {episode} {start_time} {end_time}"
        response = await self.send_command(command)
        self.assert_command_result_file_matches(response, expected_file)

    @pytest.mark.asyncio
    async def test_cut_clip_invalid_time_format(self):
        episode = "S07E06"
        start_time = "abc"
        end_time = "36:49.00"

        expected_message = await self.get_response(RK.INCORRECT_TIME_FORMAT)

        command = f"/wytnij {episode} {start_time} {end_time}"
        response = await self.send_command(command)
        await self.assert_response_contains(response, [expected_message])

    @pytest.mark.asyncio
    async def test_cut_clip_nonexistent_episode(self):
        episode = "S99E99"
        start_time = "00:00.00"
        end_time = "00:10.00"

        expected_message = await self.get_response(RK.VIDEO_FILE_NOT_EXIST)

        command = f"/wytnij {episode} {start_time} {end_time}"
        response = await self.send_command(command)
        await self.assert_response_contains(response, [expected_message])

    @pytest.mark.asyncio
    async def test_cut_clip_large_time_range(self):
        episode = "S07E06"
        start_time = "40:00.00"
        end_time = "41:00.00"

        expected_file = f"cut_{episode}_{start_time}_{end_time}.mp4"

        command = f"/wytnij {episode} {start_time} {end_time}"
        response = await self.send_command(command)
        self.assert_command_result_file_matches(response, expected_file)

    @pytest.mark.asyncio
    async def test_cut_clip_end_time_before_start_time(self):
        episode = "S07E06"
        start_time = "36:49.00"
        end_time = "36:47.50"

        expected_message =  await self.get_response(RK.END_TIME_EARLIER_THAN_START)

        command = f"/wytnij {episode} {start_time} {end_time}"
        response = await self.send_command(command)
        await self.assert_response_contains(response, [expected_message])

    @pytest.mark.asyncio
    async def test_cut_clip_exact_episode_length(self):
        await self.switch_to_normal_user()
        episode = "S07E06"
        start_time = "00:00.00"
        end_time = "45:00.00"

        expected_message = await self.get_response(RK.LIMIT_EXCEEDED_CLIP_DURATION)

        command = f"/wytnij {episode} {start_time} {end_time}"
        response = await self.send_command(command)
        await self.assert_response_contains(response, [expected_message])
