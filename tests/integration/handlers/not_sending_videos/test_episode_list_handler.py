import logging

import pytest

from bot.handlers.not_sending_videos.episode_list_handler import EpisodeListHandler
from tests.integration.base_integration_test import BaseIntegrationTest

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures("mock_db")
class TestEpisodeListHandlerIntegration(BaseIntegrationTest):

    @pytest.mark.asyncio
    async def test_episode_list_show_seasons(self, mock_db, mock_es):
        message = self.create_message('/odcinki')
        responder = self.create_responder()

        handler = EpisodeListHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send season list"

    @pytest.mark.asyncio
    async def test_episode_list_show_season_episodes(self, mock_db, mock_es):
        message = self.create_message('/episodes 1')
        responder = self.create_responder()

        handler = EpisodeListHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send episode list or error"

    @pytest.mark.asyncio
    async def test_episode_list_specials(self, mock_db, mock_es):
        for special_keyword in ['specjalne', 'specials', 'spec', 's']:
            responder = self.create_responder()
            message = self.create_message(f'/odcinki {special_keyword}')

            handler = EpisodeListHandler(message, responder, logger)
            await handler.handle()

            assert responder.has_sent_text(), f"Handler should respond to special keyword: {special_keyword}"

    @pytest.mark.asyncio
    async def test_episode_list_invalid_season_format(self, mock_db, mock_es):
        message = self.create_message('/odcinki abc')
        responder = self.create_responder()

        handler = EpisodeListHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_episode_list_too_many_arguments(self, mock_db, mock_es):
        message = self.create_message('/odcinki 1 extra')
        responder = self.create_responder()

        handler = EpisodeListHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_episode_list_negative_season(self, mock_db, mock_es):
        message = self.create_message('/episodes -1')
        responder = self.create_responder()

        handler = EpisodeListHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send response"

    @pytest.mark.asyncio
    async def test_episode_list_different_aliases(self, mock_db, mock_es):
        for command in ['/odcinki', '/episodes', '/o']:
            responder = self.create_responder()
            message = self.create_message(command)

            handler = EpisodeListHandler(message, responder, logger)
            await handler.handle()

            assert responder.has_sent_text(), f"Handler should respond to {command}"
