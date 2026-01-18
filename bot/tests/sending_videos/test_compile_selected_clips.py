import pytest

from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool")
class TestCompileSelectedClipsHandler(BaseTest):

    @pytest.mark.asyncio
    async def test_merge_multiple_clips(self):
        clips = [
            {"name": "klip1", "command": "/klip geniusz", "file": "clip_geniusz_saved.mp4"},
            {"name": "klip2", "command": "/klip kozioł", "file": "clip_kozioł_saved.mp4"},
            {"name": "klip3", "command": "/klip uczniowie", "file": "clip_uczniowie_saved.mp4"},
        ]

        for clip in clips:
            response = self.send_command(clip["command"])
            self.assert_command_result_file_matches(response, clip["file"])
            self.send_command(f'/zapisz {clip["name"]}')

        compile_params = "1 2 3"
        response = self.send_command(f'/polaczklipy {compile_params}')
        self.assert_command_result_file_matches(response, f'merged_clip_{compile_params}.mp4')

    @pytest.mark.asyncio
    async def test_merge_invalid_clip_numbers(self):
        response = self.send_command('/klip geniusz')
        self.assert_command_result_file_matches(response, 'clip_geniusz_saved.mp4')
        self.send_command('/zapisz klip1')

        response = self.send_command('/klip kozioł')
        self.assert_command_result_file_matches(response, 'clip_kozioł_saved.mp4')
        self.send_command('/zapisz klip2')

        response = self.send_command('/polaczklipy 1 5')
        self.assert_response_contains(response, [await self.get_response(RK.INVALID_ARGS_COUNT)])

    @pytest.mark.asyncio
    async def test_merge_single_clip(self):
        response = self.send_command('/klip geniusz')
        self.assert_command_result_file_matches(response, 'clip_geniusz_saved.mp4')
        self.send_command('/zapisz klip1')

        response = self.send_command('/polaczklipy 1')
        self.assert_command_result_file_matches(response, 'merged_single_clip_1.mp4')

    @pytest.mark.asyncio
    async def test_merge_no_clips(self):
        response = self.send_command('/polaczklipy 1 2')
        self.assert_response_contains(response, [await self.get_response(RK.NO_MATCHING_CLIPS_FOUND)])

    @pytest.mark.asyncio
    async def test_merge_clips_with_special_characters_in_name(self):
        response = self.send_command('/klip geniusz')
        self.assert_command_result_file_matches(response, 'clip_geniusz_saved.mp4')
        self.send_command('/zapisz klip@specjalny!')

        response = self.send_command('/polaczklipy 1')
        self.assert_command_result_file_matches(response, 'merged_special_name_clip.mp4')
