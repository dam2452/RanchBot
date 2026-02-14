import pytest

import bot.responses.not_sending_videos.transcription_handler_responses as msg
from tests.e2e.base_test import BaseTest


@pytest.mark.usefixtures("db_pool")
class TestTranscriptionHandler(BaseTest):
    @pytest.mark.asyncio
    async def test_transcription_existing_quote(self):
        response = self.send_command('/transkrypcja Nie szkoda panu tego pięknego gabinetu?')
        self.assert_message_hash_matches(response, expected_key="transcription_quote_gabinetu.message")

    @pytest.mark.asyncio
    async def test_transcription_multiple_results(self):
        response = self.send_command('/transkrypcja Wójt przyjechał.')
        self.assert_message_hash_matches(response, expected_key="transcription_quote_multiple_results.message")
