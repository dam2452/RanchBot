import logging

import pytest

from bot.handlers.administration.list_admins_handler import ListAdminsHandler
from tests.integration.base_integration_test import BaseIntegrationTest

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures("mock_db")
class TestListAdminsHandlerIntegration(BaseIntegrationTest):

    @pytest.mark.asyncio
    async def test_list_admins_with_default_admin(self, mock_db):
        message = self.create_message('/listadmins')
        responder = self.create_responder()

        handler = ListAdminsHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send admins list"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert str(self.admin_id) in all_responses

    @pytest.mark.asyncio
    async def test_list_admins_with_multiple_admins(self, mock_db):
        await self.add_test_user(user_id=66661, username='admin1')
        await self.make_user_admin(66661)
        await self.add_test_user(user_id=66662, username='admin2')
        await self.make_user_admin(66662)

        message = self.create_message('/la')
        responder = self.create_responder()

        handler = ListAdminsHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send admins list"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert '66661' in all_responses or 'admin1' in all_responses
        assert '66662' in all_responses or 'admin2' in all_responses

    @pytest.mark.asyncio
    async def test_list_admins_excludes_moderators(self, mock_db):
        await self.add_test_user(user_id=66663, username='moderator1')
        await self.make_user_moderator(66663)

        message = self.create_message('/listadmins')
        responder = self.create_responder()

        handler = ListAdminsHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send admins list"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert '66663' not in all_responses

    @pytest.mark.asyncio
    async def test_list_admins_excludes_regular_users(self, mock_db):
        await self.add_test_user(user_id=66664, username='regular_user')

        message = self.create_message('/listadmins')
        responder = self.create_responder()

        handler = ListAdminsHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send admins list"
        all_responses = ' '.join(responder.get_all_text_responses())
        if '66664' in all_responses:
            assert False, "Regular users should not appear in admins list"

    @pytest.mark.asyncio
    async def test_list_admins_after_admin_removal(self, mock_db):
        await self.add_test_user(user_id=66665, username='temp_admin')
        await self.make_user_admin(66665)
        await self.remove_admin(66665)

        message = self.create_message('/listadmins')
        responder = self.create_responder()

        handler = ListAdminsHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send admins list"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert '66665' not in all_responses
