import pytest

from bot.database.response_keys import ResponseKey as RK
from bot.tests.base_test import BaseTest

# TODO: wynik /dostosuj będzie taki sam jak wynik /adostosuj (bez ostatniego klipa nie ma offsetu_
# TODO: wynik /dostosuj wykonanego drugi raz będzie szerszy, uwzględni offset z poprzedniego wywołania
# TODO: wynik /adostosuj wykonanego drugi raz będzie identyczny

@pytest.mark.usefixtures("db_pool", "telegram_client")
class TestAdjustVideoClipHandler(BaseTest):

    @pytest.mark.asyncio
    async def test_no_previous_searches(self):
        response = await self.send_command("/dostosuj 1 10 -5")
        self.assert_response_contains(response, [await self.get_response(RK.NO_PREVIOUS_SEARCHES)])

    @pytest.mark.asyncio
    async def test_no_quotes_selected(self):
        response = await self.send_command("/dostosuj -5 10")
        self.assert_response_contains(response, [await self.get_response(RK.NO_QUOTES_SELECTED)])

    # TODO: Jakim cudem to przechodzi z 2 argami? XD
    @pytest.mark.asyncio
    async def test_invalid_args_count(self):
        video_name = "geniusz"
        await self.assert_command_result_file_matches(await self.send_command(f"/klip {video_name}"), f"clip_{video_name}.mp4")
        self.assert_response_contains(await self.send_command("/dostosuj -abc 1.2"), [await self.get_response(RK.INVALID_ARGS_COUNT)])
        self.assert_response_contains(await self.send_command("/dostosuj -abc 1.2 1.2 1.2 1.2"), [await self.get_response(RK.INVALID_ARGS_COUNT)])

    @pytest.mark.asyncio
    async def test_invalid_interval(self):
        video_name = "geniusz"
        await self.send_command(f"/szukaj {video_name}")
        response = await self.send_command("/dostosuj 1 -5.5 -15")
        self.assert_response_contains(response, [await self.get_response(RK.INVALID_INTERVAL)])

    @pytest.mark.asyncio
    async def test_invalid_segment_index(self):
        search_term = "kozioł"
        invalid_clip_number = 99999
        adjust_params = "10.0 -3"
        await self.expect_command_result_contains(f"/szukaj {search_term}", ["Wyniki wyszukiwania"])
        response = await self.send_command(f"/dostosuj {invalid_clip_number} {adjust_params}")
        self.assert_response_contains(response, [await self.get_response(RK.INVALID_SEGMENT_INDEX)])

    @pytest.mark.asyncio
    async def test_adjust_clip_with_valid_params(self):
        video_name = "geniusz"
        adjust_params = "-5.5 1.5"
        adjusted_filename = f"adjusted_{video_name}_{adjust_params}.mp4"
        await self.assert_command_result_file_matches(await self.send_command(f"/klip {video_name}"), "clip_geniusz.mp4")
        await self.assert_command_result_file_matches(await self.send_command(f"/dostosuj {adjust_params}"), adjusted_filename)

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
        await self.assert_command_result_file_matches(await self.send_command(f"/dostosuj {adjust_params}"), adjusted_filename)

    @pytest.mark.asyncio
    async def test_exceeding_adjustment_limits(self):
        video_name = "geniusz"
        large_adjust_params = "100 100"
        await self.switch_to_normal_user()
        await self.assert_command_result_file_matches(await self.send_command(f"/klip {video_name}"), "clip_geniusz.mp4")
        response = await self.send_command(f"/dostosuj {large_adjust_params}")
        self.assert_response_contains(response, [await self.get_response(RK.MAX_EXTENSION_LIMIT)])

    @pytest.mark.asyncio
    async def test_exceeding_clip_duration(self):
        video_name = "geniusz"
        large_adjust_params = "500 500"
        await self.switch_to_normal_user()
        await self.assert_command_result_file_matches(await self.send_command(f"/klip {video_name}"), "clip_geniusz.mp4")
        response = await self.send_command(f"/dostosuj {large_adjust_params}")
        self.assert_response_contains(response, [await self.get_response(RK.MAX_EXTENSION_LIMIT)])
