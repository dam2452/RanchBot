import asyncio
import os
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
import asyncpg
import bcrypt


class UserManager:
    def __init__(self):
        self.load_env_file()
        self.db_config = self._get_db_config()

    def load_env_file(self) -> None:
        env_file = Path(__file__).parent / '.env'
        if not env_file.exists():
            return

        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if self._is_valid_env_line(line):
                    key, value = line.split('=', 1)
                    if key not in os.environ:
                        os.environ[key] = value.strip()

    @staticmethod
    def _is_valid_env_line(line: str) -> bool:
        return line and not line.startswith('#') and '=' in line

    @staticmethod
    def _get_db_config() -> Dict[str, Any]:
        return {
            'host': os.getenv('POSTGRES_HOST', '192.168.1.210'),
            'port': int(os.getenv('POSTGRES_PORT', '30665')),
            'database': os.getenv('POSTGRES_DB', 'postgres'),
            'user': os.getenv('POSTGRES_USER', 'RanchBot'),
            'password': os.getenv('POSTGRES_PASSWORD', ''),
            'server_settings': {
                'search_path': os.getenv('POSTGRES_SCHEMA', 'ranczo')
            }
        }

    @staticmethod
    def hash_password(password: str) -> str:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    async def connect_to_db(self) -> asyncpg.Connection:
        schema = self.db_config['server_settings']['search_path']
        print(f"🔌 Connecting to PostgreSQL: {self.db_config['user']}@{self.db_config['host']}:"
              f"{self.db_config['port']}/{self.db_config['database']} (schema: {schema})")

        try:
            return await asyncpg.connect(**self.db_config)
        except (OSError, asyncpg.PostgresError) as e:
            print(f"❌ Connection failed: {e}")
            sys.exit(1)

    @staticmethod
    async def check_existing_user(conn: asyncpg.Connection, user_id: int, username: str) -> Optional[
        asyncpg.Record]:
        return await conn.fetchrow(
            "SELECT user_id, username FROM user_profiles WHERE user_id = $1 OR username = $2",
            user_id, username
        )

    async def update_user_password(self, conn: asyncpg.Connection, user_id: int, password: str) -> str:
        hashed_password = self.hash_password(password)
        await conn.execute(
            """
            INSERT INTO user_credentials (user_id, hashed_password)
            VALUES ($1, $2)
            ON CONFLICT (user_id) DO UPDATE SET hashed_password = EXCLUDED.hashed_password
            """,
            user_id, hashed_password
        )
        return hashed_password

    @staticmethod
    async def create_user_profile(conn: asyncpg.Connection, user_id: int, username: str,
                                  full_name: str, subscription_end: Optional[date]) -> None:
        await conn.execute(
            """
            INSERT INTO user_profiles (user_id, username, full_name, subscription_end, note)
            VALUES ($1, $2, $3, $4, $5)
            """,
            user_id, username, full_name, subscription_end, "Added via standalone script"
        )

    async def create_user_credentials(self, conn: asyncpg.Connection, user_id: int, password: str) -> str:
        hashed_password = self.hash_password(password)
        await conn.execute(
            """
            INSERT INTO user_credentials (user_id, hashed_password)
            VALUES ($1, $2)
            """,
            user_id, hashed_password
        )
        return hashed_password

    @staticmethod
    def confirm_action(message: str) -> bool:
        response = input(f"\n{message} (yes/no): ")  # pylint: disable=bad-builtin
        return response.lower() == "yes"

    @staticmethod
    def display_user_info(user_id: int, username: str, full_name: str,
                          subscription_days: int, subscription_end: Optional[date]) -> None:
        print("\n⚠️  PRODUCTION DATABASE - Confirm action:")
        print(f"   User ID: {user_id}")
        print(f"   Username: {username}")
        print(f"   Full name: {full_name}")
        print(f"   Subscription days: {subscription_days}")
        print(f"   Subscription end: {subscription_end}")

    async def handle_existing_user(self, conn: asyncpg.Connection, existing_user: asyncpg.Record,
                                   user_id: int, username: str, password: str) -> bool:
        print("\n⚠️  User already exists!")
        print(f"   Existing user_id: {existing_user['user_id']}")
        print(f"   Existing username: {existing_user['username']}")

        if not self.confirm_action("Update password for existing user?"):
            print("❌ Operation cancelled")
            return False

        hashed_password = await self.update_user_password(conn, user_id, password)
        print(f"✅ Password updated for user: {username}")
        print(f"   Hash: {hashed_password}")
        return True

    async def handle_new_user(self, conn: asyncpg.Connection, user_id: int, username: str,
                              password: str, full_name: str, subscription_days: int) -> bool:
        subscription_end = date.today() + timedelta(days=subscription_days) if subscription_days else None

        self.display_user_info(user_id, username, full_name, subscription_days, subscription_end)

        if not self.confirm_action("Add this user?"):
            print("❌ Operation cancelled")
            return False

        await self.create_user_profile(conn, user_id, username, full_name, subscription_end)
        print(f"✅ User profile created: {username} (ID: {user_id})")

        hashed_password = await self.create_user_credentials(conn, user_id, password)
        print(f"✅ Credentials added for user: {username}")
        print(f"   Username: {username}")
        print(f"   Password: {password}")
        print(f"   Hash: {hashed_password}")
        return True

    async def add_user_with_credentials(self, user_id: int, username: str, password: str,
                                        full_name: str = "Test User", subscription_days: int = 30) -> None:
        conn = await self.connect_to_db()

        try:
            existing_user = await self.check_existing_user(conn, user_id, username)

            if existing_user:
                await self.handle_existing_user(conn, existing_user, user_id, username, password)
            else:
                await self.handle_new_user(conn, user_id, username, password, full_name, subscription_days)

        finally:
            await conn.close()


class CLIParser:
    @staticmethod
    def parse_arguments(args: list) -> tuple:
        if len(args) < 4:
            CLIParser.show_usage()
            sys.exit(1)

        try:
            user_id = int(args[1])
        except ValueError:
            print(f"❌ Error: user_id must be a number, got: {args[1]}")
            sys.exit(1)

        username = args[2]
        password = args[3]
        full_name = args[4] if len(args) > 4 else "Test User"

        try:
            subscription_days = int(args[5]) if len(args) > 5 else 30
        except ValueError:
            print(f"❌ Error: subscription_days must be a number, got: {args[5]}")
            sys.exit(1)

        return user_id, username, password, full_name, subscription_days

    @staticmethod
    def show_usage() -> None:
        print("Usage: python3 add_user_standalone.py <user_id> <username> <password> [full_name] [subscription_days]")
        print("\nExample:")
        print("  python3 add_user_standalone.py 5178727150 Tomekm98 mypassword 'Tomek' 365")


async def main():
    user_id, username, password, full_name, subscription_days = CLIParser.parse_arguments(sys.argv)

    user_manager = UserManager()
    await user_manager.add_user_with_credentials(
        user_id, username, password, full_name, subscription_days
    )


if __name__ == "__main__":
    asyncio.run(main())
