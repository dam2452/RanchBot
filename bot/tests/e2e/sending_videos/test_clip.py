import pytest

from bot.tests.e2e.base_e2e_test import BaseE2ETest


class TestClipHandler(BaseE2ETest):
    @pytest.mark.asyncio
    async def test_dummy(self):
        quote = "geniusz"
        self.assert_command_result_file_matches(
            self.send_command(f'/klip {quote}'),
            f"clip_{quote}.mp4",
        )
