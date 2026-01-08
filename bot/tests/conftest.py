import asyncio
import logging
from urllib.parse import urljoin

import asyncpg
import pytest_asyncio
import requests

from bot.database.database_manager import DatabaseManager
from bot.settings import settings as main_settings
from bot.tests.settings import settings as s

logger = logging.getLogger(__name__)
_test_lock = asyncio.Lock()

@pytest_asyncio.fixture(scope="function", autouse=True)
async def db_pool():
    if DatabaseManager.pool is not None:
        await DatabaseManager.pool.close()

    async def init_connection(conn):
        await conn.execute("SET statement_timeout = '120s'")

    async def setup_connection(_):
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


class APIClient(requests.Session):
    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url if base_url.endswith("/") else f"{base_url}/"

    def request(self, method, url, *args, **kwargs):
        full_url = urljoin(self.base_url, str(url).lstrip("/"))
        return super().request(method, full_url, *args, **kwargs)

@pytest_asyncio.fixture(scope="function", autouse=True)
async def test_client(db_pool):  # pylint: disable=redefined-outer-name,unused-argument
    base_url = f"http://{s.REST_API_HOST}:{s.REST_API_PORT}/api/v1/"

    with APIClient(base_url) as client:
        yield client

@pytest_asyncio.fixture(scope="function", autouse=True)
async def prepare_database(db_pool):  # pylint: disable=redefined-outer-name,unused-argument
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

    i = 0
    for admin_id in s.ADMIN_IDS.split(","):
        await DatabaseManager.set_default_admin(
            user_id=s.DEFAULT_ADMIN,
            username=f"User{i}",
            password=s.TEST_PASSWORD.get_secret_value(),
        )
        logger.info(f"Admin with user_id {admin_id} has been added.")
        i+=i

    await asyncio.sleep(0.2)


@pytest_asyncio.fixture(scope="function", autouse=True)
async def auth_token(test_client, prepare_database):  # pylint: disable=redefined-outer-name,unused-argument
    login_response = test_client.post(
        "auth/login",
        json={
            "username": "User0",
            "password": s.TEST_PASSWORD.get_secret_value(),
        },
    )
    assert login_response.status_code == 200, f"Login failed: {login_response.text}"
    token_data = login_response.json()
    logger.info("Authenticated as '0'")

    return token_data["access_token"]
