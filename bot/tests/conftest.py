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
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def db_pool(event_loop):
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

@pytest.fixture(scope="class", autouse=True)
def test_client():
    with TestClient(app) as client:
        logger.info("TestClient started for REST API testing")
        yield client
        logger.info("TestClient closed")

@pytest.fixture(scope="session", autouse=True)
async def test_user(event_loop, db_pool):
    test_username = "test_api_user"
    test_id = 99999
    await DatabaseManager.add_user(
        user_id=test_id,
        username=test_username,
        password=s.ADMIN_PASSWORD.get_secret_value(),
        full_name="Test API User"
    )
    yield {
        "username": test_username,
        "password": s.ADMIN_PASSWORD.get_secret_value()
    }
    await DatabaseManager.remove_user(test_id)

@pytest.fixture(scope="class", autouse=True)
async def auth_token(test_client, test_user):
    login_response = test_client.post(
        "/api/v1/auth/login",
        json={
            "username": test_user["username"],
            "password": test_user["password"],
        },
    )
    assert login_response.status_code == 200, f"Login failed: {login_response.text}"
    token_data = login_response.json()
    logger.info(f"Authenticated as {test_user['username']}")
    return token_data["access_token"]

@pytest.fixture(autouse=True)
async def prepare_database(db_pool):
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