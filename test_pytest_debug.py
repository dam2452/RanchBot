import pytest
import pytest_asyncio
import asyncpg

@pytest_asyncio.fixture(scope="session")
async def test_pool():
    pool = await asyncpg.create_pool(
        host="localhost",
        port=5433,
        database="ranczo_test",
        user="test_user",
        password="test_password",
        server_settings={"search_path": "ranczo"},
        min_size=10,
        max_size=50,
        command_timeout=120,
        statement_cache_size=0,
    )
    yield pool
    await pool.close()

@pytest_asyncio.fixture(scope="session")
async def setup_data(test_pool):
    async with test_pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("SELECT 1")
    return "setup_done"

@pytest.mark.asyncio
async def test_simple_query(test_pool, setup_data):
    """Test simple query after setup"""
    row = await test_pool.fetchrow(
        "SELECT message FROM ranczo_messages WHERE handler_name = $1 AND key = $2",
        "StartHandler", "basic_message"
    )
    assert row is not None
    print(f"✓ Got message: {row['message']}")
