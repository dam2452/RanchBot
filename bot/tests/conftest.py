import asyncio
import logging

import httpx
import pytest
import pytest_asyncio

from bot.database.database_manager import DatabaseManager
from bot.platforms.rest_runner import app
from bot.tests.settings import settings as s

logger = logging.getLogger(__name__)
_test_lock = asyncio.Lock()

@pytest_asyncio.fixture(scope="function", autouse=True)
async def db_pool():
    if DatabaseManager.pool is not None:
        await DatabaseManager.pool.close()

    import asyncpg
    from bot.settings import settings as main_settings

    async def init_connection(conn):
        await conn.execute("SET statement_timeout = '120s'")

    async def setup_connection(conn):
        """Called when connection is acquired from pool"""
        pass

    config = {
        "host": s.TEST_POSTGRES_HOST,
        "port": s.TEST_POSTGRES_PORT,
        "database": s.TEST_POSTGRES_DB,
        "user": s.TEST_POSTGRES_USER,
        "password": s.TEST_POSTGRES_PASSWORD.get_secret_value(),
        "server_settings": {"search_path": main_settings.POSTGRES_SCHEMA},
        "min_size": 10,
        "max_size": 50,
        "command_timeout": 120,
        "max_inactive_connection_lifetime": 300,
        "statement_cache_size": 0,
        "max_cached_statement_lifetime": 0,
        "init": init_connection,
        "setup": setup_connection,
        "reset": None,  # Disable connection reset on release
    }
    DatabaseManager.pool = await asyncpg.create_pool(**config)
    await DatabaseManager.init_db()
    DatabaseManager._db_fully_initialized = True
    yield
    if DatabaseManager.pool is not None:
        await DatabaseManager.pool.close()

@pytest_asyncio.fixture(scope="function", autouse=True)
async def test_client(db_pool):
    """Create AsyncClient for testing REST API."""
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    from contextlib import asynccontextmanager
    from fastapi import FastAPI
    from bot.platforms import rest_runner

    original_limiter = rest_runner.limiter
    rest_runner.limiter = Limiter(key_func=get_remote_address, enabled=False)

    @asynccontextmanager
    async def empty_lifespan(app_instance: FastAPI):
        app_instance.state.limiter = rest_runner.limiter
        logger.info("Test lifespan: DB already initialized by db_pool fixture")
        yield
        logger.info("Test lifespan: cleanup")

    test_app = FastAPI(
        title="Ranczo Bot API v1 (Test)",
        lifespan=empty_lifespan,
    )
    test_app.add_middleware = app.add_middleware
    test_app.include_router(app.router)

    async with httpx.AsyncClient(app=test_app, base_url="http://test") as client:
        logger.info("AsyncClient started for REST API testing")
        yield client
        logger.info("AsyncClient closed")

    rest_runner.limiter = original_limiter

@pytest_asyncio.fixture(scope="function", autouse=True)
async def test_user(db_pool):
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

@pytest_asyncio.fixture(scope="function", autouse=True)
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
async def prepare_database(db_pool, test_user):
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

    test_username = "test_api_user"
    test_id = 99999
    await DatabaseManager.add_user(
        user_id=test_id,
        username=test_username,
        full_name="Test API User"
    )
    await DatabaseManager.add_user_password(test_id, test_user["password"])
    logger.info(f"Test user {test_username} has been restored after database cleanup.")

    await asyncio.sleep(0.2)
