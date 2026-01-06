import pytest

from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool", "test_client", "auth_token")
class TestSimple(BaseTest):

    @pytest.mark.asyncio
    async def test_simple_api_call(self):
        response = await self.client.post(
            f"/api/v1/start",
            json={"args": [], "reply_json": True},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        assert response.status_code == 200
