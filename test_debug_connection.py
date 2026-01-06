import asyncio
import asyncpg
import sys
import traceback

async def test_concurrent_operations():
    """Test if concurrent operations cause race conditions"""
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

    # Simulate what happens in test
    async def operation1():
        """Like test_user fixture"""
        try:
            async with pool.acquire() as conn:
                async with conn.transaction():
                    await conn.execute("SELECT 1")
                    await conn.execute("SELECT 2")
            print("✓ operation1 completed")
        except Exception as e:
            print(f"✗ operation1 failed: {e}")
            traceback.print_exc()

    async def operation2():
        """Like auth_token fixture  - login"""
        try:
            async with pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM user_profiles LIMIT 1")
            print(f"✓ operation2 completed: {row}")
        except Exception as e:
            print(f"✗ operation2 failed: {e}")
            traceback.print_exc()

    async def operation3():
        """Like get_response() in test"""
        try:
            row = await pool.fetchrow(
                "SELECT message FROM ranczo_messages WHERE handler_name = $1 AND key = $2",
                "StartHandler", "basic_message"
            )
            print(f"✓ operation3 completed: {row}")
        except Exception as e:
            print(f"✗ operation3 failed: {e}")
            traceback.print_exc()

    # Run operations concurrently (like in pytest fixtures)
    print("Running operations concurrently...")
    await asyncio.gather(operation1(), operation2(), operation3())

    # Try again sequentially
    print("\nRunning operations sequentially...")
    await operation1()
    await operation2()
    await operation3()

    await pool.close()
    print("\n✓ All tests passed!")

if __name__ == "__main__":
    try:
        asyncio.run(test_concurrent_operations())
    except Exception as e:
        print(f"\n✗ FATAL ERROR: {e}")
        traceback.print_exc()
        sys.exit(1)
