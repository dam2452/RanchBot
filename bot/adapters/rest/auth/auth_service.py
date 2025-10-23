from datetime import (
    UTC,
    datetime,
    timedelta,
)
from typing import Optional

from fastapi import HTTPException
from jose import (
    JWTError,
    jwt,
)
from passlib.context import CryptContext

from bot.database.database_manager import DatabaseManager
from bot.database.models import (
    RefreshToken,
    UserProfile,
)
from bot.exceptions import TooManyActiveTokensError
from bot.settings import settings as s

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


async def authenticate_user(username: str, password: str) -> Optional[UserProfile]:
    result = await DatabaseManager.get_credentials_with_profile_by_username(username)
    dummy_hash = "$2b$12$XEMBQhCuW2tw8rAIIoKV1ejU7nee6VDFZ5tRETJbkAQI2WCUDPqIm"

    if result is None:
        verify_password(password, dummy_hash)
        return None

    user_profile, hashed_password = result
    if not verify_password(password, hashed_password):
        return None

    return user_profile

def create_access_token(user: UserProfile, expires_minutes: int = s.JWT_EXPIRE_MINUTES) -> str:
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=expires_minutes)
    payload = {
        "user_id": user.user_id,
        "username": user.username,
        "full_name": user.full_name,
        "exp": expire.timestamp(),
        "iat": now.timestamp(),
        "iss": s.JWT_ISSUER,
        "aud": s.JWT_AUDIENCE,
    }
    return jwt.encode(payload, s.JWT_SECRET_KEY, algorithm=s.JWT_ALGORITHM)


async def create_refresh_token(
    user: UserProfile,
    ip_address: Optional[str],
    user_agent: Optional[str],
    expires_days: int = 30,
) -> str:
    now = datetime.now(UTC)
    expires_at = now + timedelta(days=expires_days)
    payload = {
        "user_id": user.user_id,
        "exp": expires_at.timestamp(),
        "iat": now.timestamp(),
        "iss": s.JWT_ISSUER,
        "aud": s.JWT_AUDIENCE,
    }
    token = jwt.encode(payload, s.JWT_SECRET_KEY, algorithm=s.JWT_ALGORITHM)

    try:
        await DatabaseManager.insert_refresh_token(
            user_id=user.user_id,
            token=token,
            created_at=now,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    except TooManyActiveTokensError as exc:
        raise HTTPException(
            status_code=429,
            detail="Too many active refresh tokens. Please log out from other sessions.",
        ) from exc

    return token


async def verify_refresh_token(token: str) -> Optional[RefreshToken]:
    try:
        jwt.decode(
            token,
            s.JWT_SECRET_KEY,
            algorithms=[s.JWT_ALGORITHM],
            issuer=s.JWT_ISSUER,
            audience=s.JWT_AUDIENCE,
        )
    except JWTError:
        return None

    return await DatabaseManager.get_refresh_token(token)


async def revoke_refresh_token(token: str) -> None:
    await DatabaseManager.revoke_refresh_token(token)


async def revoke_all_user_refresh_tokens(user_id: int) -> int:
    return await DatabaseManager.revoke_all_user_tokens(user_id)
