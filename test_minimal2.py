import asyncio
import asyncpg

async def test_empty_table_query():
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

    # Simulate what get_response() does - query from empty table
    print("Test: Query from empty table (like get_response does)")
    async with pool.acquire() as conn:
        query = """
            SELECT message
            FROM ranczo_messages
            WHERE handler_name = $1 AND key = $2
        """
        row = await conn.fetchrow(query, "StartHandler", "basic_message")
        print(f"Result: {row}")

    # Try again
    print("\nTest 2: Another query right after")
    async with pool.acquire() as conn:
        query = """
            SELECT message
            FROM ranczo_messages
            WHERE handler_name = $1 AND key = $2
        """
        row = await conn.fetchrow(query, "StartHandler", "basic_message")
        print(f"Result: {row}")

    await pool.close()
    print("\nAll tests passed!")

if __name__ == "__main__":
    asyncio.run(test_empty_table_query())
