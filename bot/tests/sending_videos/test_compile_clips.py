import pytest

from bot.database.response_keys import ResponseKey as RK
from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool")
class TestCompileClipsHandler(BaseTest):
    __SEARCH_TERM_KOZIOL = "kozioł"
    __SEARCH_TERM_ANGLII = "Anglii"
    __SEARCH_TERM_GENIUSZ = "geniusz"
    __SEARCH_TERM_BRAK_KLIPOW = "brak_klipów"

    @pytest.mark.asyncio
    async def test_compile_clip_range(self):
        message = await self.send_command(f'/szukaj {self.__SEARCH_TERM_KOZIOL}')
        self.assert_message_hash_matches(message, expected_key="search_kozioł_results.message")

        response = await self.send_command('/kompiluj 1-4')
        self.assert_command_result_file_matches(response, 'compile_kozioł_1-4.mp4')

    @pytest.mark.asyncio
    async def test_compile_specific_clips(self):
        message = await self.send_command(f'/szukaj {self.__SEARCH_TERM_KOZIOL}')
        self.assert_message_hash_matches(message, expected_key="search_kozioł_results.message")

        response = await self.send_command('/kompiluj 1 3 5')
        self.assert_command_result_file_matches(response, 'compile_kozioł_1_3_5.mp4')

    @pytest.mark.asyncio
    async def test_compile_invalid_range(self):
        message = await self.send_command(f'/szukaj {self.__SEARCH_TERM_KOZIOL}')
        self.assert_message_hash_matches(message, expected_key="search_kozioł_results.message")

        response = await self.send_command('/kompiluj 5-3')
        await self.assert_response_contains(response, [await self.get_response(RK.INVALID_RANGE, ["5-3"])])

    @pytest.mark.asyncio
    async def test_compile_invalid_index(self):
        message = await self.send_command(f'/szukaj {self.__SEARCH_TERM_KOZIOL}')
        self.assert_message_hash_matches(message, expected_key="search_kozioł_results.message")

        response = await self.send_command('/kompiluj abc')
        await self.assert_response_contains(response, [await self.get_response(RK.INVALID_INDEX, ["abc"])])

    @pytest.mark.asyncio
    async def test_compile_all_clips(self):
        message = await self.send_command(f'/szukaj {self.__SEARCH_TERM_ANGLII}')
        self.assert_message_hash_matches(message, expected_key="search_anglii_results.message")

        response = await self.send_command('/kompiluj wszystko')
        self.assert_command_result_file_matches(response, 'compile_anglii_all.mp4')

    @pytest.mark.asyncio
    async def test_no_previous_search_results(self):
        response = await self.send_command('/kompiluj wszystko')
        await self.assert_response_contains(response, [await self.get_response(RK.NO_PREVIOUS_SEARCH_RESULTS)])

    @pytest.mark.asyncio
    async def test_no_matching_segments_found(self):
        message = await self.send_command(f'/szukaj {self.__SEARCH_TERM_BRAK_KLIPOW}')
        self.assert_message_hash_matches(message, expected_key="search_no_clips_results.message")

        response = await self.send_command('/kompiluj 1-5')
        await self.assert_response_contains(response, [await self.get_response(RK.NO_PREVIOUS_SEARCH_RESULTS)])

    @pytest.mark.asyncio
    async def test_compile_exceeding_max_clips(self):
        await self.switch_to_normal_user()
        message = await self.send_command(f'/szukaj {self.__SEARCH_TERM_ANGLII}')
        self.assert_message_hash_matches(message, expected_key="search_anglii_results.message")

        response = await self.send_command('/kompiluj 1-1000')
        await self.assert_response_contains(response, [await self.get_response(RK.MAX_CLIPS_EXCEEDED)])


    @pytest.mark.asyncio
    async def test_compile_exceeding_total_duration(self):
        await self.switch_to_normal_user()
        message = await self.send_command(f'/szukaj {self.__SEARCH_TERM_GENIUSZ}')
        self.assert_message_hash_matches(message, expected_key="search_geniusz_results.message")

        response = await self.send_command('/kompiluj 1-25')
        await self.assert_response_contains(response, [await self.get_response(RK.CLIP_TIME_EXCEEDED)])
