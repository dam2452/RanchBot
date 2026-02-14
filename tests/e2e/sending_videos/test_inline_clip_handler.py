import pytest

from tests.e2e.base_test import BaseTest


@pytest.mark.usefixtures("db_pool")
class TestInlineClipHandler(BaseTest):
    @pytest.mark.asyncio
    async def test_inline_with_saved_compilation(self):
        self.send_command("/szukaj piwo")
        self.send_command("/kompiluj 1 2 3")
        self.send_command("/zapisz piwo")

        response = self.send_command("/inline piwo")

        self.assert_command_result_file_matches(
            response, "inline_piwo.zip",
        )

