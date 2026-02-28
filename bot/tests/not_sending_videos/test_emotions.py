import pytest

import bot.responses.not_sending_videos.emotions_handler_responses as msg
from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool")
class TestEmotionsHandler(BaseTest):

    @pytest.mark.asyncio
    async def test_emotions_list_returns_emotions(self):
        response = self.send_command('/emocje')
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_emotions_list_short_alias(self):
        response_full = self.send_command('/emocje')
        response_alias = self.send_command('/e')
        assert response_full.status_code == 200
        assert response_alias.status_code == 200

    @pytest.mark.asyncio
    async def test_emotions_list_alias_emotion(self):
        response = self.send_command('/emotion')
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_emotions_list_contains_polish_names(self):
        response = self.send_command('/emocje')
        polish_labels = list(msg.EMOTION_PL_MAP.values())
        response_text = response.json().get("content", "")
        has_any = any(label in response_text for label in polish_labels)
        if not has_any:
            self.assert_response_contains(response, [msg.get_no_emotions_message()])

    @pytest.mark.asyncio
    async def test_emotions_no_data_graceful(self):
        response = self.send_command('/emocje')
        assert response.status_code == 200
        content = response.json().get("content", "")
        assert content, "Response should not be empty"
