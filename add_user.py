"""Script to add a user with credentials to the database."""
import asyncio
import sys

from bot.adapters.rest.auth.auth_service import hash_password
from bot.database.database_manager import DatabaseManager


async def add_user_with_credentials(user_id: int, username: str, password: str, full_name: str = "Test User"):
    """Add a user with credentials to the database."""
    await DatabaseManager.ensure_db_initialized()

    # Add user profile
    await DatabaseManager.add_user(
        user_id=user_id,
        username=username,
        full_name=full_name,
        note="Added via script",
        subscription_days=30,
    )
    print(f"✅ User profile created: {username} (ID: {user_id})")

    # Add credentials
    hashed_password = hash_password(password)
    async with DatabaseManager.get_db_connection() as conn:
        await conn.execute(
            """
            INSERT INTO user_credentials (user_id, hashed_password)
            VALUES ($1, $2)
            ON CONFLICT (user_id) DO UPDATE SET hashed_password = EXCLUDED.hashed_password
            """,
            user_id, hashed_password,
        )
    print(f"✅ Credentials added for user: {username}")
    print(f"   Username: {username}")
    print(f"   Password: {password}")
    print(f"   Hash: {hashed_password}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python add_user.py <user_id> <username> <password>")
        sys.exit(1)

    user_id = int(sys.argv[1])
    username = sys.argv[2]
    password = sys.argv[3]

    asyncio.run(add_user_with_credentials(user_id, username, password))
