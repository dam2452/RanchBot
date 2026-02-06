import pytest

from bot.database.database_manager import DatabaseManager


@pytest.mark.asyncio
async def test_get_user_active_series_default(db_pool):  # pylint: disable=unused-argument
    user_id = 999999
    await DatabaseManager.add_user(user_id, "test_user", "Test User")
    series = await DatabaseManager.get_user_active_series(user_id)
    assert series == "ranczo"
    await DatabaseManager.remove_user(user_id)


@pytest.mark.asyncio
async def test_set_and_get_user_active_series(db_pool):  # pylint: disable=unused-argument
    user_id = 999999
    await DatabaseManager.add_user(user_id, "test_user", "Test User")
    await DatabaseManager.set_user_active_series(user_id, "kiepscy")
    series = await DatabaseManager.get_user_active_series(user_id)
    assert series == "kiepscy"
    await DatabaseManager.remove_user(user_id)


@pytest.mark.asyncio
async def test_update_existing_series_context(db_pool):  # pylint: disable=unused-argument
    user_id = 999999
    await DatabaseManager.add_user(user_id, "test_user", "Test User")
    await DatabaseManager.set_user_active_series(user_id, "ranczo")
    await DatabaseManager.set_user_active_series(user_id, "alternatywy4")
    series = await DatabaseManager.get_user_active_series(user_id)
    assert series == "alternatywy4"
    await DatabaseManager.remove_user(user_id)


@pytest.mark.asyncio
async def test_trigger_auto_create_context():
    user_id = 888888

    await DatabaseManager.add_user(
        user_id=user_id,
        username="testuser",
        full_name="Test User",
    )

    series = await DatabaseManager.get_user_active_series(user_id)
    assert series == "ranczo"

    await DatabaseManager.remove_user(user_id)
