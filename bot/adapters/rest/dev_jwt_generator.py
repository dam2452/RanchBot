from datetime import (
    UTC,
    datetime,
    timedelta,
)

import click
from dotenv import load_dotenv
from jose import jwt

from bot.settings import settings as s

load_dotenv()

def generate_token(user_id: int, username: str, full_name: str, expire_minutes: int) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=expire_minutes)
    payload = {
        "user_id": user_id,
        "username": username,
        "full_name": full_name,
        "iat": datetime.now(UTC).timestamp(),
        "exp": expire.timestamp(),
    }
    return jwt.encode(payload, s.JWT_SECRET_KEY, algorithm=s.JWT_ALGORITHM)

@click.command()
@click.option("--user-id", "-u", required=True, type=int, help="User ID from database")
@click.option("--username", "-n", required=True, type=str, help="Username")
@click.option("--full-name", "-f", required=True, type=str, help="User full name")
@click.option("--expire-minutes", "-e", default=s.JWT_EXPIRE_MINUTES, show_default=True, type=int, help="Expiration time in minutes")
def cli(user_id: int, username: str, full_name: str, expire_minutes: int):
    token = generate_token(user_id, username, full_name, expire_minutes)
    click.echo(token)

if __name__ == "__main__":
    cli() # pylint: disable=no-value-for-parameter
