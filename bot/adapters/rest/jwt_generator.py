from datetime import (
    UTC,
    datetime,
    timedelta,
)

from dotenv import load_dotenv
from jose import jwt

from bot.settings import settings as s

load_dotenv()


def generate_token(user_id: int, username: str, full_name: str) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=s.JWT_EXPIRE_MINUTES)
    payload = {
        "user_id": user_id,
        "username": username,
        "full_name": full_name,
        "exp": expire,
    }
    return jwt.encode(payload, s.JWT_SECRET_KEY, algorithm=s.JWT_ALGORITHM)


if __name__ == "__main__":
    token = generate_token(2015344951, "dam2452", "Damian Koterba")
    print(token)
