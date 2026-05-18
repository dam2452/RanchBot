import pytest

from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool")
class TestBatchHandler(BaseTest):

    @pytest.mark.asyncio
    async def test_batch_multiple_valid_commands(self):
        response = self.client.post(
            "batch",
            json={
                "commands": [
                    {"command": "szukaj", "args": ["geniusz"]},
                    {"command": "szukaj", "args": ["kozioł"]},
                ],
            },
            headers={"Authorization": f"Bearer {self.token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "summary" in data
        assert data["summary"]["total"] == 2
        assert data["results"][0]["command"] == "szukaj"
        assert data["results"][0]["status"] == "success"
        assert data["results"][1]["command"] == "szukaj"
        assert data["results"][1]["status"] == "success"

    @pytest.mark.asyncio
    async def test_batch_unknown_command_continues(self):
        response = self.client.post(
            "batch",
            json={
                "commands": [
                    {"command": "szukaj", "args": ["geniusz"]},
                    {"command": "nieistnieje", "args": []},
                    {"command": "szukaj", "args": ["kozioł"]},
                ],
            },
            headers={"Authorization": f"Bearer {self.token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["total"] == 3
        assert data["results"][1]["status"] == "error"
        assert "Unknown command" in data["results"][1]["error"]
        assert data["results"][0]["status"] == "success"
        assert data["results"][2]["status"] == "success"

    @pytest.mark.asyncio
    async def test_batch_empty_commands_rejected(self):
        response = self.client.post(
            "batch",
            json={"commands": []},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_batch_too_many_commands_rejected(self):
        commands = [{"command": "szukaj", "args": ["test"]} for _ in range(21)]
        response = self.client.post(
            "batch",
            json={"commands": commands},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_batch_unauthorized(self):
        response = self.client.post(
            "batch",
            json={"commands": [{"command": "szukaj", "args": ["test"]}]},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_batch_summary_counts(self):
        response = self.client.post(
            "batch",
            json={
                "commands": [
                    {"command": "nieistnieje", "args": []},
                    {"command": "szukaj", "args": ["geniusz"]},
                ],
            },
            headers={"Authorization": f"Bearer {self.token}"},
        )
        data = response.json()
        assert data["summary"]["succeeded"] == 1
        assert data["summary"]["failed"] == 1
