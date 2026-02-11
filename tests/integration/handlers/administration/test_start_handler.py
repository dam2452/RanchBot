import logging

import pytest

from bot.handlers.administration.start_handler import StartHandler
from tests.integration.base_integration_test import BaseIntegrationTest

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures("mock_db")
class TestStartHandlerIntegration(BaseIntegrationTest):

    @pytest.mark.asyncio
    async def test_start_basic_message(self, mock_db):
        message = self.create_message('/start')
        responder = self.create_responder()

        handler = StartHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send basic message"

    @pytest.mark.asyncio
    async def test_start_help_alias(self, mock_db):
        message = self.create_message('/help')
        responder = self.create_responder()

        handler = StartHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should respond to /help"

    @pytest.mark.asyncio
    async def test_start_pomoc_alias(self, mock_db):
        message = self.create_message('/pomoc')
        responder = self.create_responder()

        handler = StartHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should respond to /pomoc"

    @pytest.mark.asyncio
    async def test_start_with_lista_argument(self, mock_db):
        for keyword in ['lista', 'list', 'l']:
            message = self.create_message(f'/start {keyword}')
            responder = self.create_responder()

            handler = StartHandler(message, responder, logger)
            await handler.handle()

            assert responder.has_sent_text(), f"Handler should respond to 'start {keyword}'"

    @pytest.mark.asyncio
    async def test_start_with_wszystko_argument(self, mock_db):
        for keyword in ['wszystko', 'all', 'a']:
            message = self.create_message(f'/start {keyword}')
            responder = self.create_responder()

            handler = StartHandler(message, responder, logger)
            await handler.handle()

            assert responder.has_sent_text(), f"Handler should respond to 'start {keyword}'"

    @pytest.mark.asyncio
    async def test_start_with_wyszukiwanie_argument(self, mock_db):
        for keyword in ['wyszukiwanie', 'search', 's']:
            message = self.create_message(f'/start {keyword}')
            responder = self.create_responder()

            handler = StartHandler(message, responder, logger)
            await handler.handle()

            assert responder.has_sent_text(), f"Handler should respond to 'start {keyword}'"

    @pytest.mark.asyncio
    async def test_start_with_edycja_argument(self, mock_db):
        for keyword in ['edycja', 'edit', 'e']:
            message = self.create_message(f'/start {keyword}')
            responder = self.create_responder()

            handler = StartHandler(message, responder, logger)
            await handler.handle()

            assert responder.has_sent_text(), f"Handler should respond to 'start {keyword}'"

    @pytest.mark.asyncio
    async def test_start_with_zarzadzanie_argument(self, mock_db):
        for keyword in ['zarzadzanie', 'management', 'm']:
            message = self.create_message(f'/start {keyword}')
            responder = self.create_responder()

            handler = StartHandler(message, responder, logger)
            await handler.handle()

            assert responder.has_sent_text(), f"Handler should respond to 'start {keyword}'"

    @pytest.mark.asyncio
    async def test_start_with_raportowanie_argument(self, mock_db):
        for keyword in ['raportowanie', 'reporting', 'r']:
            message = self.create_message(f'/start {keyword}')
            responder = self.create_responder()

            handler = StartHandler(message, responder, logger)
            await handler.handle()

            assert responder.has_sent_text(), f"Handler should respond to 'start {keyword}'"

    @pytest.mark.asyncio
    async def test_start_with_subskrypcje_argument(self, mock_db):
        for keyword in ['subskrypcje', 'subscriptions', 'sub']:
            message = self.create_message(f'/start {keyword}')
            responder = self.create_responder()

            handler = StartHandler(message, responder, logger)
            await handler.handle()

            assert responder.has_sent_text(), f"Handler should respond to 'start {keyword}'"

    @pytest.mark.asyncio
    async def test_start_with_skroty_argument(self, mock_db):
        for keyword in ['skroty', 'shortcuts', 'sh']:
            message = self.create_message(f'/start {keyword}')
            responder = self.create_responder()

            handler = StartHandler(message, responder, logger)
            await handler.handle()

            assert responder.has_sent_text(), f"Handler should respond to 'start {keyword}'"

    @pytest.mark.asyncio
    async def test_start_with_invalid_argument(self, mock_db):
        message = self.create_message('/start invalid_command')
        responder = self.create_responder()

        handler = StartHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message for invalid command"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert 'nieprawidłow' in all_responses.lower() or 'invalid' in all_responses.lower() or 'błąd' in all_responses.lower()

    @pytest.mark.asyncio
    async def test_start_with_too_many_arguments(self, mock_db):
        message = self.create_message('/start lista extra argument')
        responder = self.create_responder()

        handler = StartHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"
