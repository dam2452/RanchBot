import asyncio
import logging

import httpx
import pytest

from bot.database.database_manager import DatabaseManager
from bot.tests.settings import settings as s

logger = logging.getLogger(__name__)

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def db_pool():
    await DatabaseManager.init_pool(
        host=s.TEST_POSTGRES_HOST,
        port=s.TEST_POSTGRES_PORT,
        database=s.TEST_POSTGRES_DB,
        user=s.TEST_POSTGRES_USER,
        password=s.TEST_POSTGRES_PASSWORD.get_secret_value(),
    )
    await DatabaseManager.init_db()
    yield
    await DatabaseManager.pool.close()

@pytest.fixture(scope="class")
async def http_client():
    async with httpx.AsyncClient(
        base_url=s.REST_API_BASE_URL,
        timeout=30.0,
    ) as client:
        logger.info("HTTP client started for REST API testing")
        yield client
        logger.info("HTTP client disconnected")

@pytest.fixture(scope="class")
async def auth_token(http_client):
    login_response = await http_client.post(
        "/auth/login",
        json={
            "username": s.ADMIN_USERNAME,
            "password": s.ADMIN_PASSWORD.get_secret_value(),
        },
    )
    assert login_response.status_code == 200, f"Login failed: {login_response.text}"
    token_data = login_response.json()
    logger.info(f"Authenticated as {s.ADMIN_USERNAME}")
    return token_data["access_token"]

@pytest.fixture(autouse=True)
async def prepare_database():
    tables_to_clear = [
        "user_profiles",
        "user_roles",
        "user_logs",
        "system_logs",
        "video_clips",
        "reports",
        "search_history",
        "last_clips",
        "subscription_keys",
        "user_command_limits",
    ]
    await DatabaseManager.clear_test_db(tables=tables_to_clear, schema="ranczo")
    logger.info("The specified test database tables have been cleared.")

    await DatabaseManager.set_default_admin(
        user_id=s.DEFAULT_ADMIN,
        username=s.ADMIN_USERNAME,
        full_name=s.ADMIN_FULL_NAME,
    )
    logger.info(f"Default admin with user_id {s.DEFAULT_ADMIN} has been set.")
