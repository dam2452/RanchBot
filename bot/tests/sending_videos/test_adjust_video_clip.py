import pytest

from bot.database.response_keys import ResponseKey as RK
from bot.tests.base_test import BaseTest

@pytest.mark.usefixtures("db_pool", "telegram_client")
class TestAdjustVideoClipHandler(BaseTest):
    async def __execute_both_variants(self, command_args: str, response_key: str):
        expected_response =  await self.get_response(response_key)
        await self.expect_command_result_contains(f"/d {command_args}", [expected_response])
        await self.expect_command_result_contains(f"/ad {command_args}", [expected_response])

    @pytest.mark.asyncio
    async def test_no_previous_searches(self):
        await self.__execute_both_variants("1 10 -5", RK.NO_PREVIOUS_SEARCHES)

    @pytest.mark.asyncio
    async def test_no_quotes_selected(self):
        await self.__execute_both_variants("-5 10", RK.NO_QUOTES_SELECTED)

    @pytest.mark.asyncio
    async def test_invalid_args_count(self):
        video_name = "geniusz"
        await self.assert_command_result_file_matches(await self.send_command(f"/klip {video_name}"), f"clip_{video_name}.mp4")

        await self.__execute_both_variants("-abc 1.2", RK.INVALID_ARGS_COUNT)
        await self.__execute_both_variants("-abc 1.2 1.2 1.2 1.2", RK.INVALID_ARGS_COUNT)

    @pytest.mark.asyncio
    async def test_invalid_interval(self):
        video_name = "geniusz"
        await self.send_command(f"/szukaj {video_name}")

        await self.__execute_both_variants("1 -5.5 -15", RK.INVALID_INTERVAL)

    @pytest.mark.asyncio
    async def test_invalid_segment_index(self):
        search_term = "kozioł"
        invalid_clip_number = 99999
        adjust_params = "10.0 -3"
        await self.expect_command_result_contains(f"/szukaj {search_term}", ["Wyniki wyszukiwania"])

        await self.__execute_both_variants(f"{invalid_clip_number} {adjust_params}", RK.INVALID_SEGMENT_INDEX)

    @pytest.mark.asyncio
    async def test_adjust_clip_with_valid_params(self):
        video_name = "geniusz"
        adjust_params = "-5.5 1.5"
        adjusted_filename = f"adjusted_{video_name}_{adjust_params}.mp4"
        await self.assert_command_result_file_matches(await self.send_command(f"/klip {video_name}"), "clip_geniusz.mp4")

        await self.assert_command_result_file_matches(await self.send_command(f"/d {adjust_params}"), adjusted_filename)
        await self.assert_command_result_file_matches(await self.send_command(f"/ad {adjust_params}"), adjusted_filename)

    @pytest.mark.asyncio
    async def test_consecutive_absolute_adjustments(self):
        video_name = "geniusz"
        adjust_params = "10.0 -3"
        adjusted_filename = f"adjusted_{video_name}_{adjust_params}.mp4"
        await self.assert_command_result_file_matches(await self.send_command(f"/klip {video_name}"), "clip_geniusz.mp4")

        await self.assert_command_result_file_matches(await self.send_command(f"/ad {adjust_params}"), adjusted_filename)
        await self.assert_command_result_file_matches(await self.send_command(f"/ad {adjust_params}"), adjusted_filename)

    @pytest.mark.asyncio
    async def test_consecutive_relative_adjustments(self):
        video_name = "geniusz"
        adjust_params = "10.0 -3"
        adjusted_filename = f"adjusted_{video_name}_{adjust_params}.mp4"
        adjusted_filename_2 = f"adjusted_{video_name}_20.0_-6.mp4"
        await self.assert_command_result_file_matches(await self.send_command(f"/klip {video_name}"), "clip_geniusz.mp4")

        await self.assert_command_result_file_matches(await self.send_command(f"/d {adjust_params}"), adjusted_filename)
        await self.assert_command_result_file_matches(await self.send_command(f"/d {adjust_params}"), adjusted_filename_2)

    @pytest.mark.asyncio
    async def test_adjust_clip_with_three_params(self):
        search_term = "kozioł"
        clip_number = 2
        adjust_params = f"{clip_number} 10.0 -3"
        adjusted_filename = f"adjusted_{search_term}_clip{clip_number}_{adjust_params}.mp4"
        await self.expect_command_result_contains(f"/szukaj {search_term}", ["Wyniki wyszukiwania"])
        await self.assert_command_result_file_matches(
            await self.send_command(f"/wybierz {clip_number}"),
            f"clip_{search_term}_clip{clip_number}.mp4",
        )

        await self.assert_command_result_file_matches(await self.send_command(f"/d {adjust_params}"), adjusted_filename)
        await self.assert_command_result_file_matches(await self.send_command(f"/ad {adjust_params}"), adjusted_filename)

    @pytest.mark.asyncio
    async def test_exceeding_adjustment_limits(self):
        video_name = "geniusz"
        large_adjust_params = "100 100"
        await self.switch_to_normal_user()
        await self.assert_command_result_file_matches(await self.send_command(f"/klip {video_name}"), "clip_geniusz.mp4")

        await self.__execute_both_variants(large_adjust_params, RK.MAX_EXTENSION_LIMIT)