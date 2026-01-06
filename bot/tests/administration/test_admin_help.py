import pytest

from bot.database.response_keys import ResponseKey as RK
from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool", "test_client", "auth_token")
class TestAdminHelpHandler(BaseTest):
    @pytest.mark.asyncio
    async def test_admin_help(self):
        import requests
        BASE_URL = "http://192.168.1.210:8199/api/v1"

        login_payload = {
            "username": "Admin",
            "password": "qykjeq-9sybqo-joJfyq"
        }

        with requests.Session() as session:
            response = session.post(f"{BASE_URL}/auth/login", json=login_payload)
            response.raise_for_status()

            token = response.json()["access_token"]

            # Authorized Request
            headers = {
                "Authorization": f"Bearer {token}"
            }

            response_start = session.post(
                f"{BASE_URL}/admin",
                json={},
                headers=headers
            )
            response_start.raise_for_status()

            print(response_start.status_code)
            print(response_start.text)

            assert response_start.status_code == 200
            assert response_start.text is not None

        self.expect_command_result_contains(
            'admin',
            [await self.remove_first_line(await self.get_response(RK.ADMIN_HELP))],
        )

    @pytest.mark.skip(reason="ashdahsd")
    @pytest.mark.asyncio
    async def test_admin_shortcuts(self):
        self.expect_command_result_contains(
            'admin',
            [await self.remove_first_line(await self.get_response(RK.ADMIN_SHORTCUTS))],
            args=['skroty']
        )

    @pytest.mark.skip(reason="ashdahsd")
    @pytest.mark.asyncio
    async def test_admin_invalid_command(self):
        self.expect_command_result_contains(
            'admin',
            [await self.remove_first_line(await self.get_response(RK.ADMIN_HELP))],
            args=['nieistniejace_polecenie']
        )
