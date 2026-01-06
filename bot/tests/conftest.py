import asyncio
import logging

import httpx
import pytest_asyncio
from bot.platforms.rest_runner import app

from bot.database.database_manager import DatabaseManager
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
    import sys
    from bot.settings import settings as main_settings

    if 'bot.platforms.rest_runner' in sys.modules:
        del sys.modules['bot.platforms.rest_runner']

    original_flag = main_settings.DISABLE_RATE_LIMITING
    main_settings.DISABLE_RATE_LIMITING = True

    async with httpx.AsyncClient(app=app, base_url="http://192.168.1.210:8199") as client:
        logger.info("AsyncClient started for REST API testing")
        yield client
        logger.info("AsyncClient closed")

    main_settings.DISABLE_RATE_LIMITING = original_flag

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
        password=s.ADMIN_PASSWORD.get_secret_value()
    )
    logger.info(f"Default admin with user_id {s.DEFAULT_ADMIN} has been set.")
    await asyncio.sleep(1)


@pytest_asyncio.fixture(scope="function", autouse=True)
async def auth_token(test_client, prepare_database):
    login_response = await test_client.post(
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