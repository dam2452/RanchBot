import logging

import pytest

from bot.handlers.administration.update_user_note_handler import UpdateUserNoteHandler
from tests.integration.base_integration_test import BaseIntegrationTest

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures("mock_db")
class TestUpdateUserNoteHandlerIntegration(BaseIntegrationTest):

    @pytest.mark.asyncio
    async def test_update_user_note_success(self, mock_db):
        await self.add_test_user(user_id=88881)

        message = self.create_message('/note 88881 Test note content')
        responder = self.create_responder()

        handler = UpdateUserNoteHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send success message"
        user = mock_db.get_user(88881)
        assert user['note'] == 'Test note content', "Note should be updated"

    @pytest.mark.asyncio
    async def test_update_user_note_with_long_text(self, mock_db):
        await self.add_test_user(user_id=88882)
        long_note = 'This is a very long note ' * 20

        message = self.create_message(f'/note 88882 {long_note}')
        responder = self.create_responder()

        handler = UpdateUserNoteHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send success message"
        user = mock_db.get_user(88882)
        assert user['note'] == long_note, "Long note should be updated"

    @pytest.mark.asyncio
    async def test_update_user_note_with_special_characters(self, mock_db):
        await self.add_test_user(user_id=88883)
        special_note = 'Note with !@#$%^&*() special chars'

        message = self.create_message(f'/note 88883 {special_note}')
        responder = self.create_responder()

        handler = UpdateUserNoteHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send success message"
        user = mock_db.get_user(88883)
        assert user['note'] == special_note

    @pytest.mark.asyncio
    async def test_update_user_note_replace_existing(self, mock_db):
        await self.add_test_user(user_id=88884)
        await mock_db.update_user_note(88884, 'Old note')

        message = self.create_message('/note 88884 New note')
        responder = self.create_responder()

        handler = UpdateUserNoteHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send success message"
        user = mock_db.get_user(88884)
        assert user['note'] == 'New note', "Note should be replaced"

    @pytest.mark.asyncio
    async def test_update_user_note_missing_arguments(self, mock_db):
        message = self.create_message('/note')
        responder = self.create_responder()

        handler = UpdateUserNoteHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_update_user_note_missing_note_content(self, mock_db):
        message = self.create_message('/note 88885')
        responder = self.create_responder()

        handler = UpdateUserNoteHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_update_user_note_invalid_user_id_format(self, mock_db):
        message = self.create_message('/note abc Some note')
        responder = self.create_responder()

        handler = UpdateUserNoteHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_update_user_note_negative_user_id(self, mock_db):
        message = self.create_message('/note -123 Some note')
        responder = self.create_responder()

        handler = UpdateUserNoteHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_update_user_note_nonexistent_user(self, mock_db):
        message = self.create_message('/note 99999 Note for nonexistent user')
        responder = self.create_responder()

        handler = UpdateUserNoteHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send success message"

    @pytest.mark.asyncio
    async def test_update_user_note_with_unicode(self, mock_db):
        await self.add_test_user(user_id=88886)
        unicode_note = 'Notatka z polskimi znakami: ąćęłńóśźż 🎉'

        message = self.create_message(f'/note 88886 {unicode_note}')
        responder = self.create_responder()

        handler = UpdateUserNoteHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send success message"
        user = mock_db.get_user(88886)
        assert user['note'] == unicode_note
