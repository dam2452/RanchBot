import pytest

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
    async def test_inline_with_saved_compilation(self):
        self.send_command("/szukaj piwo")
        self.send_command("/kompiluj 1 2 3")
        self.send_command("/zapisz piwo")

        response = self.send_command("/inline piwo")

        self.assert_command_result_file_matches(
            response, "inline_piwo.zip",
        )

    @pytest.mark.asyncio
    async def test_inline_no_results(self):
        clip = "shafbhasfhbasfhbashfbashfbahsfb"
        self.expect_command_result_contains(
            f"/inline {clip}",
            [f"Nie znaleziono klipów dla zapytania: \"{clip}\""],
        )
