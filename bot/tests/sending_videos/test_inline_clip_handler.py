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

        self.assert_command_result_file_matches(
            response, "inline_duda.zip",
        )

    @pytest.mark.asyncio
    async def test_inline_1_saved_4_search_results(self):
        self.send_command('/klip ksiądz')
        self.send_command('/zapisz ksiądz')

        response = self.send_command('/inline ksiądz')

        self.assert_command_result_file_matches(
            response, "inline_ksiadz.zip",
        )

    @pytest.mark.asyncio
    async def test_inline_no_results(self):
        clip = "shafbhasfhbasfhbashfbashfbahsfb"
        self.expect_command_result_contains(
            f"/inline {clip}",
            [f"Nie znaleziono klipów dla zapytania: \"{clip}\""],
        )
