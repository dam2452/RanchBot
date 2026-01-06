import asyncio
import asyncpg

async def test_basic_connection():
    pool = await asyncpg.create_pool(
        host="localhost",
        port=5433,
        database="ranczo_test",
        user="test_user",
        password="test_password",
        server_settings={"search_path": "ranczo"},
        min_size=5,
        max_size=20,
        command_timeout=60,
    )

    # Test 1: Simple query
    async with pool.acquire() as conn:
        result = await conn.fetchval("SELECT 1")
        print(f"Test 1 passed: {result}")

    # Test 2: Two queries in sequence without transaction
    async with pool.acquire() as conn:
        await conn.execute("SELECT 1")
        await conn.execute("SELECT 2")
        print("Test 2 passed")

    # Test 3: Two queries in sequence WITH transaction
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("SELECT 1")
            await conn.execute("SELECT 2")
        print("Test 3 passed")

    # Test 4: Query that doesn't exist (like our case)
    try:
        async with pool.acquire() as conn:
            await conn.fetchrow("SELECT * FROM nonexistent_table")
    except Exception as e:
        print(f"Test 4: Expected error: {type(e).__name__}")

    # Test 5: After error, try another query
    try:
        async with pool.acquire() as conn:
            result = await conn.fetchval("SELECT 3")
            print(f"Test 5 passed: {result}")
    except Exception as e:
        print(f"Test 5 FAILED: {e}")

    await pool.close()

if __name__ == "__main__":
    asyncio.run(test_basic_connection())
