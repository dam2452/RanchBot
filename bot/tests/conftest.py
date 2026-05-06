import asyncio
from datetime import (
    datetime,
    timedelta,
    timezone,
)
import logging
from urllib.parse import urljoin

import pytest_asyncio
import requests

from bot.database.database_manager import DatabaseManager
from bot.search.infra.elastic_search_manager import ElasticSearchManager
from bot.tests.settings import settings as s

logger = logging.getLogger(__name__)
_test_lock = asyncio.Lock()

@pytest_asyncio.fixture(scope="function", autouse=True)
async def reset_es_client():
    ElasticSearchManager._shared_es_client = None
    yield
    if ElasticSearchManager._shared_es_client is not None:
        await ElasticSearchManager._shared_es_client.close()
    ElasticSearchManager._shared_es_client = None


@pytest_asyncio.fixture(scope="function", autouse=True)
async def db_pool():
    await DatabaseManager.init_pool(
        host=s.TEST_POSTGRES_HOST,
        port=s.TEST_POSTGRES_PORT,
        database=s.TEST_POSTGRES_DB,
        user=s.TEST_POSTGRES_USER,
        password=s.TEST_POSTGRES_PASSWORD.get_secret_value(),
        schema=s.POSTGRES_SCHEMA,
    )
    await DatabaseManager.init_db()
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
        "video_clips",
        "reports",
        "search_history",
        "last_clips",
        "subscription_keys",
        "user_command_limits",
        "user_search_filters",
        "verification_tokens",
    ]
    await DatabaseManager.clear_test_db(tables=tables_to_clear, schema="ranczo")
    logger.info("The specified test database tables have been cleared.")

    i = 0
    for admin_id in s.TEST_ADMINS.split(","):
        await DatabaseManager.set_default_admin(
            user_id=int(admin_id),
            username=f"TestUser{i}",
            full_name=f"TestUser{i}",
            password=s.TEST_PASSWORD.get_secret_value(),
        )
        logger.info(f"Admin with user_id {admin_id} has been added.")
        i+=1

    first_admin_id = int(s.TEST_ADMINS.split(",")[0])
    await DatabaseManager.store_verification_token(
        user_id=first_admin_id,
        token="jakiskod",
        purpose="telegram_link",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    logger.info("Seeded 'jakiskod' verification token for test_link_already_linked.")


@pytest_asyncio.fixture(scope="function", autouse=True)
async def auth_token(test_client, prepare_database):  # pylint: disable=redefined-outer-name,unused-argument
    login_response = test_client.post(
        "auth/login",
        json={
            "username": "TestUser0",
            "password": s.TEST_PASSWORD.get_secret_value(),
        },
    )
    assert login_response.status_code == 200, f"Login failed: {login_response.text}"
    token_data = login_response.json()
    logger.info("Authenticated as 'TestUser0'")

    return token_data["access_token"]
