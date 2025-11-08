import asyncio
import sys

from bot.adapters.rest.auth.auth_service import hash_password
from bot.database.database_manager import DatabaseManager


async def add_user_with_credentials(user_id: int, username: str, password: str, full_name: str = "Test User"):
    await DatabaseManager.ensure_db_initialized()

    async with DatabaseManager.get_db_connection() as conn:
        existing_user = await conn.fetchrow(
            "SELECT user_id, username FROM user_profiles WHERE user_id = $1 OR username = $2",
            user_id, username,
        )
        if existing_user:
            print(f"❌ Error: User already exists!")
            print(f"   Existing user_id: {existing_user['user_id']}")
            print(f"   Existing username: {existing_user['username']}")
            print("\n⚠️  Use different user_id and username to avoid conflicts.")
            return

    print(f"\n⚠️  PRODUCTION DATABASE - Confirm action:")
    print(f"   User ID: {user_id}")
    print(f"   Username: {username}")
    print(f"   Full name: {full_name}")
    response = input("Add this user? (yes/no): ")
    if response.lower() != "yes":
        print("❌ Operation cancelled")
        return

    await DatabaseManager.add_user(
        user_id=user_id,
        username=username,
        full_name=full_name,
        note="Added via script",
        subscription_days=30,
    )
    print(f"✅ User profile created: {username} (ID: {user_id})")

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
