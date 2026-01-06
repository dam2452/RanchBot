import pytest

from bot.database.response_keys import ResponseKey as RK
from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool")
class TestTranscriptionHandler(BaseTest):

    @pytest.mark.asyncio
    async def test_transcription_existing_quote(self):
        response = self.send_command('/transkrypcja Nie szkoda panu tego pięknego gabinetu?')
        self.assert_message_hash_matches(response, expected_key="transcription_quote_gabinetu.message")

    @pytest.mark.asyncio
    async def test_transcription_nonexistent_quote(self):
        response = self.send_command('/transkrypcja asdfghijk')
        self.assert_message_hash_matches(response, expected_key="transcription_quote_nonexistent.message")

    @pytest.mark.asyncio
    async def test_transcription_no_arguments(self):
        response = self.send_command('/transkrypcja')
        self.assert_response_contains(
            response,
            [await self.get_response(RK.NO_QUOTE_PROVIDED)],
        )

    @pytest.mark.asyncio
    async def test_transcription_valid_with_context(self):
        response = self.send_command('/transkrypcja Ale co to za geniusz?')
        self.assert_message_hash_matches(response, expected_key="transcription_quote_geniusz.message")

    @pytest.mark.asyncio
    async def test_transcription_multiple_results(self):
        response = self.send_command('/transkrypcja Wójt przyjechał.')
        self.assert_message_hash_matches(response, expected_key="transcription_quote_multiple_results.message")

    @pytest.mark.asyncio
    async def test_transcription_with_invalid_characters(self):
        response = self.send_command('/transkrypcja $$$%%%^^^')
        self.assert_message_hash_matches(response, expected_key="transcription_quote_invalid.message")

    @pytest.mark.asyncio
    async def test_transcription_not_found_in_context(self):
        response = self.send_command('/transkrypcja Jakieś losowe zdanie.')
        self.assert_message_hash_matches(response, expected_key="transcription_quote_not_found.message")
