import pytest

import bot.responses.sending_videos.adjust_video_clip_handler_responses as msg
from tests.e2e.base_test import BaseTest


@pytest.mark.usefixtures("db_pool")
class TestAdjustVideoClipHandler(BaseTest):
    def __execute_both_variants(self, command_args: str, expected_message: str):
        self.expect_command_result_contains(f"/d {command_args}", [expected_message])
        self.expect_command_result_contains(f"/ad {command_args}", [expected_message])

    @pytest.mark.asyncio
    async def test_no_previous_searches(self):
        self.__execute_both_variants("1 10 -5", msg.get_no_previous_searches_message())

    @pytest.mark.asyncio
    async def test_no_quotes_selected(self):
        self.__execute_both_variants("-5 10", msg.get_no_quotes_selected_message())

    @pytest.mark.asyncio
    async def test_invalid_args_count(self):
        video_name = "geniusz"
        self.assert_command_result_file_matches(self.send_command(f"/klip {video_name}"), f"clip_{video_name}.mp4")

        self.__execute_both_variants("-abc", msg.get_invalid_args_count_message())
        self.__execute_both_variants("-abc 1.2", msg.get_invalid_args_count_message())
        self.__execute_both_variants("-abc 1.2 1.2 1.2 1.2", msg.get_invalid_args_count_message())

    @pytest.mark.asyncio
    async def test_invalid_interval(self):
        video_name = "geniusz"
        self.send_command(f"/szukaj {video_name}")

        self.__execute_both_variants("1 -5.5 -15", msg.get_invalid_interval_message())

    @pytest.mark.asyncio
    async def test_invalid_segment_index(self):
        search_term = "kozioł"
        invalid_clip_number = 99999
        adjust_params = "10.0 -3"
        self.expect_command_result_contains(f"/szukaj {search_term}", ["Wyniki wyszukiwania"])

        self.__execute_both_variants(f"{invalid_clip_number} {adjust_params}", msg.get_invalid_segment_index_message())

    @pytest.mark.asyncio
    async def test_adjust_clip_with_valid_params(self):
        video_name = "geniusz"
        adjust_params = "-5.5 1.5"
        adjusted_filename = f"adjusted_{video_name}_{adjust_params}.mp4"
        self.assert_command_result_file_matches(self.send_command(f"/klip {video_name}"), "clip_geniusz.mp4")

        self.assert_command_result_file_matches(self.send_command(f"/d {adjust_params}"), adjusted_filename)
        self.assert_command_result_file_matches(self.send_command(f"/ad {adjust_params}"), adjusted_filename)

    @pytest.mark.asyncio
    async def test_consecutive_absolute_adjustments(self):
        video_name = "geniusz"
        adjust_params = "10.0 -3"
        adjusted_filename = f"adjusted_{video_name}_{adjust_params}.mp4"
        self.assert_command_result_file_matches(self.send_command(f"/klip {video_name}"), "clip_geniusz.mp4")

        self.assert_command_result_file_matches(self.send_command(f"/ad {adjust_params}"), adjusted_filename)
        self.assert_command_result_file_matches(self.send_command(f"/ad {adjust_params}"), adjusted_filename)

    @pytest.mark.asyncio
    async def test_consecutive_relative_adjustments(self):
        video_name = "geniusz"
        adjust_params = "10.0 -3"
        adjusted_filename = f"adjusted_{video_name}_{adjust_params}.mp4"
        adjusted_filename_2 = f"adjusted_{video_name}_20.0_-6.mp4"
        self.assert_command_result_file_matches(self.send_command(f"/klip {video_name}"), "clip_geniusz.mp4")

        self.assert_command_result_file_matches(self.send_command(f"/d {adjust_params}"), adjusted_filename)
        self.assert_command_result_file_matches(self.send_command(f"/d {adjust_params}"), adjusted_filename_2)

    @pytest.mark.asyncio
    async def test_adjust_clip_with_three_params(self):
        search_term = "kozioł"
        clip_number = 2
        adjust_params = f"{clip_number} 10.0 -3"
        adjusted_filename = f"adjusted_{search_term}_clip{clip_number}_{adjust_params}.mp4"
        self.expect_command_result_contains(f"/szukaj {search_term}", ["Wyniki wyszukiwania"])
        self.assert_command_result_file_matches(
            self.send_command(f"/wybierz {clip_number}"),
            f"clip_{search_term}_clip{clip_number}.mp4",
        )

        self.assert_command_result_file_matches(self.send_command(f"/d {adjust_params}"), adjusted_filename)
        self.assert_command_result_file_matches(self.send_command(f"/ad {adjust_params}"), adjusted_filename)

    @pytest.mark.asyncio
    async def test_exceeding_adjustment_limits(self):
        video_name = "geniusz"
        large_adjust_params = "100 100"
        await self.switch_to_normal_user()
        self.assert_command_result_file_matches(self.send_command(f"/klip {video_name}"), "clip_geniusz.mp4")

        self.__execute_both_variants(large_adjust_params, msg.get_max_extension_limit_message())
