import pytest

import bot.responses.not_sending_videos.serial_context_handler_responses as msg
from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool")
class TestSerialContextHandler(BaseTest):

    @pytest.mark.asyncio
    async def test_serial_without_args(self):
        response = self.send_command('/serial')
        self.assert_response_contains(response, ["WYBÓR SERIALU", "Dostępne seriale"])

    @pytest.mark.asyncio
    async def test_serial_change_to_ranczo(self):
        response = self.send_command('/serial ranczo')
        self.assert_response_contains(response, [msg.get_serial_changed_message("ranczo")])

    @pytest.mark.asyncio
    async def test_serial_invalid_name(self):
        response = self.send_command('/serial nieistniejacy')
        self.assert_response_contains(response, ["Nieznany serial: Nieistniejacy"])

    @pytest.mark.asyncio
    async def test_serial_short_alias(self):
        response = self.send_command('/ser ranczo')
        self.assert_response_contains(response, [msg.get_serial_changed_message("ranczo")])
