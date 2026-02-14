import logging

import pytest

from bot.handlers.administration.list_moderators_handler import ListModeratorsHandler
from tests.integration.base_integration_test import BaseIntegrationTest

logger = logging.getLogger(__name__)


class TestListModeratorsHandlerIntegration(BaseIntegrationTest):

    @pytest.mark.asyncio
    async def test_list_moderators_with_multiple_moderators(self, mock_db):
        await self.add_test_user(user_id=77771, username='moderator1')
        mock_db._roles[77771] = ['moderator']
        await self.add_test_user(user_id=77772, username='moderator2')
        mock_db._roles[77772] = ['moderator']

        message = self.create_message('/listmoderators')
        responder = self.create_responder()

        handler = ListModeratorsHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send moderators list"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert '77771' in all_responses or 'moderator1' in all_responses
        assert '77772' in all_responses or 'moderator2' in all_responses

    @pytest.mark.asyncio
    async def test_list_moderators_when_no_moderators(self):
        message = self.create_message('/lm')
        responder = self.create_responder()

        handler = ListModeratorsHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send empty message"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert 'nie znaleziono' in all_responses.lower() or 'not found' in all_responses.lower()

    @pytest.mark.asyncio
    async def test_list_moderators_excludes_admins(self):
        await self.add_test_user(user_id=77773, username='admin1')
        await self.make_user_admin(77773)

        message = self.create_message('/listmoderators')
        responder = self.create_responder()

        handler = ListModeratorsHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send moderators list"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert '77773' not in all_responses or 'brak' in all_responses.lower()

    @pytest.mark.asyncio
    async def test_list_moderators_excludes_regular_users(self):
        await self.add_test_user(user_id=77774, username='regular_user')

        message = self.create_message('/listmoderators')
        responder = self.create_responder()

        handler = ListModeratorsHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send moderators list"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert 'nie znaleziono' in all_responses.lower() or 'not found' in all_responses.lower()

    @pytest.mark.asyncio
    async def test_list_moderators_with_single_moderator(self, mock_db):
        await self.add_test_user(user_id=77775, username='single_mod')
        mock_db._roles[77775] = ['moderator']

        message = self.create_message('/listmoderators')
        responder = self.create_responder()

        handler = ListModeratorsHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send moderators list"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert '77775' in all_responses or 'single_mod' in all_responses
