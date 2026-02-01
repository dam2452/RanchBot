import io
import zipfile

import pytest

import bot.responses.sending_videos.clip_handler_responses as msg
from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool")
class TestInlineClipHandler(BaseTest):

    @pytest.mark.asyncio
    async def test_inline_5_search_results(self):
        response = self.send_command('/inline duda')

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert 'application' in response.headers.get('content-type', ''), "Response should be a file"

        with zipfile.ZipFile(io.BytesIO(response.content), 'r') as zip_ref:
            file_list = zip_ref.namelist()
            assert len(file_list) == 5, f"Expected 5 files in ZIP, got {len(file_list)}"

            for idx, filename in enumerate(sorted(file_list), start=1):
                assert filename.startswith(f"{idx}_search_"), f"File {filename} should start with {idx}_search_"
                assert filename.endswith('.mp4'), f"File {filename} should be an mp4"

    @pytest.mark.asyncio
    async def test_inline_1_saved_4_search_results(self):
        self.send_command('/klip ksiądz')
        self.send_command('/zapisz ksiądz')

        response = self.send_command('/inline ksiądz')

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert 'application' in response.headers.get('content-type', ''), "Response should be a file"

        with zipfile.ZipFile(io.BytesIO(response.content), 'r') as zip_ref:
            file_list = sorted(zip_ref.namelist())
            assert len(file_list) == 5, f"Expected 5 files in ZIP (1 saved + 4 search), got {len(file_list)}"

            first_file = file_list[0]
            assert first_file.startswith("1_saved_"), f"First file should be saved clip, got {first_file}"
            assert "ksiądz" in first_file.lower(), f"Saved clip should contain 'ksiądz' in name"

            for idx, filename in enumerate(file_list[1:], start=2):
                assert filename.startswith(f"{idx}_search_"), f"File {filename} should start with {idx}_search_"
                assert filename.endswith('.mp4'), f"File {filename} should be an mp4"

    @pytest.mark.asyncio
    async def test_inline_no_results(self):
        self.expect_command_result_contains(
            '/inline shafbhasfhbasfhbashfbashfbahsfb',
            ['Nie znaleziono klipu dla'],
        )
