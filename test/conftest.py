import asyncio
import logging

import pytest_asyncio

from bot.database.database_manager import DatabaseManager
from bot.tests.settings import settings as s

logger = logging.getLogger(__name__)

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
