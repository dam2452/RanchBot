import pytest

from bot.tests.base_test import BaseTest

_TEST_OBJECT = "person"
_NONEXISTENT_OBJECT = "nieistniejacy_obiekt_xyzzy_9999"


@pytest.mark.usefixtures("db_pool")
class TestObjectsHandler(BaseTest):

    @pytest.mark.asyncio
    async def test_objects_list_no_args(self):
        response = self.send_command('/obiekt')
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_objects_list_alias_obj(self):
        response = self.send_command('/obj')
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_objects_list_alias_object(self):
        response = self.send_command('/object')
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_objects_by_class_existing(self):
        response = self.send_command(f'/obiekt {_TEST_OBJECT}')
        assert response.status_code == 200
        content = response.json().get("content", "")
        has_scenes = _TEST_OBJECT.lower() in content.lower()
        has_not_found = "nie znaleziono" in content.lower()
        assert has_scenes or has_not_found

    @pytest.mark.asyncio
    async def test_objects_by_class_nonexistent(self):
        response = self.send_command(f'/obiekt {_NONEXISTENT_OBJECT}')
        self.assert_response_contains(
            response,
            [f"Nie znaleziono scen z obiektem '{_NONEXISTENT_OBJECT}'"],
        )

    @pytest.mark.asyncio
    async def test_objects_sorted_by_count_desc(self):
        response = self.send_command(f'/obiekt {_TEST_OBJECT}')
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_objects_filter_exact(self):
        response = self.send_command(f'/obiekt {_TEST_OBJECT} =1')
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_objects_filter_greater_than(self):
        response = self.send_command(f'/obiekt {_TEST_OBJECT} >2')
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_objects_filter_less_than(self):
        response = self.send_command(f'/obiekt {_TEST_OBJECT} <5')
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_objects_filter_gte(self):
        response = self.send_command(f'/obiekt {_TEST_OBJECT} >=3')
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_objects_filter_lte(self):
        response = self.send_command(f'/obiekt {_TEST_OBJECT} <=4')
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_objects_filter_no_operator_means_exact(self):
        r1 = self.send_command(f'/obiekt {_TEST_OBJECT} 4')
        r2 = self.send_command(f'/obiekt {_TEST_OBJECT} =4')
        assert r1.status_code == 200
        assert r2.status_code == 200

    @pytest.mark.asyncio
    async def test_objects_invalid_filter(self):
        response = self.send_command(f'/obiekt {_TEST_OBJECT} niepoprawny_filtr')
        self.assert_response_contains(
            response,
            ["NIEPOPRAWNY FILTR"],
        )
