import asyncio
import logging

import pytest
from fastapi.testclient import TestClient

from bot.database.database_manager import DatabaseManager
from bot.platforms.rest_runner import app
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
def test_client():
    """Create FastAPI TestClient for testing REST API."""
    with TestClient(app) as client:
        logger.info("TestClient started for REST API testing")
        yield client
        logger.info("TestClient closed")

@pytest.fixture(scope="class")
def auth_token(test_client):
    """Authenticate and return access token for the default admin user."""
    login_response = test_client.post(
        "/api/v1/auth/login",
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
