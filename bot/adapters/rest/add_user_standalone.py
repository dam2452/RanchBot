import asyncio
from datetime import (
    date,
    timedelta,
)
from typing import (
    Any,
    Dict,
    Optional,
)

import asyncpg
import bcrypt
import click


class StandaloneUserAdder:
    def __init__(self, db_config: Dict[str, Any]):
        self.__db_config = db_config

    async def add_user_with_credentials(
        self, user_id: int, username: str, password: str,
        full_name: str = "Test User", subscription_days: int = 30,
    ) -> None:
        conn = await self.__connect_to_db()

        try:
            existing_user = await self.__check_existing_user(conn, user_id, username)

            if existing_user:
                await self.__handle_existing_user(conn, existing_user, user_id, username, password)
            else:
                await self.__handle_new_user(conn, user_id, username, password, full_name, subscription_days)

        finally:
            await conn.close()

    @staticmethod
    def __hash_password(password: str) -> str:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    async def __connect_to_db(self) -> asyncpg.Connection:
        schema = self.__db_config['server_settings']['search_path']
        print(f"Connecting to PostgreSQL: {self.__db_config['user']}@{self.__db_config['host']}:"
              f"{self.__db_config['port']}/{self.__db_config['database']} (schema: {schema})")

        try:
            return await asyncpg.connect(**self.__db_config)
        except (OSError, asyncpg.PostgresError) as e:
            print(f"Connection failed: {e}")
            raise

    @staticmethod
    async def __check_existing_user(conn: asyncpg.Connection, user_id: int, username: str) -> Optional[
        asyncpg.Record
    ]:
        return await conn.fetchrow(
            "SELECT user_id, username FROM user_profiles WHERE user_id = $1 OR username = $2",
            user_id, username,
        )

    async def __update_user_password(self, conn: asyncpg.Connection, user_id: int, password: str) -> str:
        hashed_password = self.__hash_password(password)
        await conn.execute(
            """
            INSERT INTO user_credentials (user_id, hashed_password)
            VALUES ($1, $2)
            ON CONFLICT (user_id) DO UPDATE SET hashed_password = EXCLUDED.hashed_password
            """,
            user_id, hashed_password,
        )
        return hashed_password

    @staticmethod
    async def __create_user_profile(
        conn: asyncpg.Connection, user_id: int, username: str,
        full_name: str, subscription_end: Optional[date],
    ) -> None:
        await conn.execute(
            """
            INSERT INTO user_profiles (user_id, username, full_name, subscription_end, note)
            VALUES ($1, $2, $3, $4, $5)
            """,
            user_id, username, full_name, subscription_end, "Added via standalone script",
        )

    async def __create_user_credentials(self, conn: asyncpg.Connection, user_id: int, password: str) -> str:
        hashed_password = self.__hash_password(password)
        await conn.execute(
            """
            INSERT INTO user_credentials (user_id, hashed_password)
            VALUES ($1, $2)
            """,
            user_id, hashed_password,
        )
        return hashed_password

    @staticmethod
    def __confirm_action(message: str) -> bool:
        response = input(f"\n{message} (yes/no): ")  # pylint: disable=bad-builtin
        return response.lower() == "yes"

    @staticmethod
    def __display_user_info(
        user_id: int, username: str, full_name: str,
        subscription_days: int, subscription_end: Optional[date],
    ) -> None:
        print("\nPRODUCTION DATABASE - Confirm action:")
        print(f"   User ID: {user_id}")
        print(f"   Username: {username}")
        print(f"   Full name: {full_name}")
        print(f"   Subscription days: {subscription_days}")
        print(f"   Subscription end: {subscription_end}")

    async def __handle_existing_user(
        self, conn: asyncpg.Connection, existing_user: asyncpg.Record,
        user_id: int, username: str, password: str,
    ) -> bool:
        print("\nUser already exists!")
        print(f"   Existing user_id: {existing_user['user_id']}")
        print(f"   Existing username: {existing_user['username']}")

        if not self.__confirm_action("Update password for existing user?"):
            print("Operation cancelled")
            return False

        hashed_password = await self.__update_user_password(conn, user_id, password)
        print(f"Password updated for user: {username}")
        print(f"   Hash: {hashed_password}")
        return True

    async def __handle_new_user(
        self, conn: asyncpg.Connection, user_id: int, username: str,
        password: str, full_name: str, subscription_days: int,
    ) -> bool:
        subscription_end = date.today() + timedelta(days=subscription_days) if subscription_days else None

        self.__display_user_info(user_id, username, full_name, subscription_days, subscription_end)

        if not self.__confirm_action("Add this user?"):
            print("Operation cancelled")
            return False

        await self.__create_user_profile(conn, user_id, username, full_name, subscription_end)
        print(f"User profile created: {username} (ID: {user_id})")

        hashed_password = await self.__create_user_credentials(conn, user_id, password)
        print(f"Credentials added for user: {username}")
        print(f"   Username: {username}")
        print(f"   Password: {password}")
        print(f"   Hash: {hashed_password}")
        return True

@click.command()
@click.argument('user_id', type=int)
@click.argument('username')
@click.argument('password')
@click.option('--full-name', default='Test User', help='Full name of the user')
@click.option('--subscription-days', default=30, type=int, help='Number of subscription days')
@click.option('--db-host', required=True, help='PostgreSQL host')
@click.option('--db-port', type=int, required=True, help='PostgreSQL port')
@click.option('--db-name', required=True, help='Database name')
@click.option('--db-user', required=True, help='Database user')
@click.option('--db-password', required=True, help='Database password')
@click.option('--db-schema', default='ranczo', help='Database schema')
def main(  # pylint: disable=too-many-arguments
    user_id: int, username: str, password: str, full_name: str, subscription_days: int,
    db_host: str, db_port: int, db_name: str, db_user: str, db_password: str, db_schema: str,
):
    db_config = {
        'host': db_host,
        'port': db_port,
        'database': db_name,
        'user': db_user,
        'password': db_password,
        'server_settings': {
            'search_path': db_schema,
        },
    }

    adder = StandaloneUserAdder(db_config)
    asyncio.run(
        adder.add_user_with_credentials(
            user_id, username, password, full_name, subscription_days,
        ),
    )


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
