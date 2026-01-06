import asyncio
import logging

import httpx
import pytest
import pytest_asyncio

from bot.database.database_manager import DatabaseManager
from bot.platforms.rest_runner import app
from bot.tests.settings import settings as s

logger = logging.getLogger(__name__)

@pytest_asyncio.fixture(scope="session")
async def event_loop():
    loop = asyncio.new_event_loop()

@pytest_asyncio.fixture(scope="session", autouse=True)
async def db_pool(event_loop):
    if DatabaseManager.pool is not None:
        await DatabaseManager.pool.close()

    await DatabaseManager.init_pool(
        host=s.TEST_POSTGRES_HOST,
        port=s.TEST_POSTGRES_PORT,
        database=s.TEST_POSTGRES_DB,
        user=s.TEST_POSTGRES_USER,
        password=s.TEST_POSTGRES_PASSWORD.get_secret_value(),
    )
    await DatabaseManager.init_db()
    yield
    if DatabaseManager.pool is not None:
        await DatabaseManager.pool.close()

@pytest.fixture(scope="class", autouse=True)
async def test_client():
    """Create AsyncClient for testing REST API."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        logger.info("AsyncClient started for REST API testing")
        yield client
        logger.info("AsyncClient closed")

@pytest_asyncio.fixture(scope="session", autouse=True)
async def test_user(event_loop, db_pool):
    test_username = "test_api_user"
    test_id = 99999

    try:
        await DatabaseManager.remove_user(test_id)
    except:
        pass

    await DatabaseManager.add_user(
        user_id=test_id,
        username=test_username,
        full_name="Test API User"
    )
    await DatabaseManager.add_user_password(test_id, s.ADMIN_PASSWORD.get_secret_value())
    yield {
        "username": test_username,
        "password": s.ADMIN_PASSWORD.get_secret_value()
    }
    await DatabaseManager.remove_user(test_id)

@pytest_asyncio.fixture(scope="class", autouse=True)
async def auth_token(test_client, test_user):
    """Authenticate and return access token for the test user."""
    login_response = await test_client.post(
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

@pytest_asyncio.fixture(autouse=True)
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
