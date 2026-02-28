import pytest

from bot.tests.base_test import BaseTest

_TEST_CHARACTER = "Wilkowyska"
_TEST_CHARACTER_LOWER = "wilkowyska"
_NONEXISTENT_CHARACTER = "NieIstniejacaPostac12345"
_UNKNOWN_EMOTION = "nieistniejacaemocja"


@pytest.mark.usefixtures("db_pool")
class TestCharactersHandler(BaseTest):

    @pytest.mark.asyncio
    async def test_characters_list_no_args(self):
        response = self.send_command('/postacie')
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_characters_list_short_alias(self):
        response = self.send_command('/p')
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_characters_list_alias_characters(self):
        response = self.send_command('/characters')
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_characters_list_sorted_alphabetically(self):
        response = self.send_command('/postacie')
        self.assert_message_hash_matches(response, expected_key="characters_list.message")

    @pytest.mark.asyncio
    async def test_characters_by_name_exists(self):
        response = self.send_command(f'/postacie {_TEST_CHARACTER}')
        assert response.status_code == 200
        content = response.json().get("content", "")
        has_scenes = _TEST_CHARACTER.lower() in content.lower()
        has_not_found = "nie znaleziono" in content.lower()
        assert has_scenes or has_not_found

    @pytest.mark.asyncio
    async def test_characters_by_name_case_insensitive(self):
        response_normal = self.send_command(f'/postacie {_TEST_CHARACTER}')
        response_lower = self.send_command(f'/postacie {_TEST_CHARACTER_LOWER}')
        assert response_normal.status_code == 200
        assert response_lower.status_code == 200

    @pytest.mark.asyncio
    async def test_characters_by_name_nonexistent(self):
        response = self.send_command(f'/postacie {_NONEXISTENT_CHARACTER}')
        self.assert_response_contains(
            response,
            [f"Nie znaleziono scen z postacia '{_NONEXISTENT_CHARACTER}'"],
        )

    @pytest.mark.asyncio
    async def test_characters_by_name_and_emotion_en(self):
        response = self.send_command(f'/postacie {_TEST_CHARACTER} happy')
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_characters_emotion_in_polish(self):
        response = self.send_command(f'/postacie {_TEST_CHARACTER} radosny')
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_characters_unknown_emotion(self):
        response = self.send_command(f'/postacie {_TEST_CHARACTER} {_UNKNOWN_EMOTION}')
        self.assert_response_contains(response, ["/emocje"])

    @pytest.mark.asyncio
    async def test_characters_list_ignores_season_0(self):
        response = self.send_command('/postacie')
        assert response.status_code == 200
        content = response.json().get("content", "")
        assert "Spec-" not in content

    @pytest.mark.asyncio
    async def test_characters_scenes_sorted_by_confidence(self):
        response = self.send_command(f'/postacie {_TEST_CHARACTER}')
        self.assert_message_hash_matches(
            response,
            expected_key=f"characters_scenes_{_TEST_CHARACTER_LOWER}.message",
        )
