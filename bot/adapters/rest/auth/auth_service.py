from datetime import datetime, timedelta, UTC
import secrets
from passlib.context import CryptContext
from jose import jwt
from bot.database.database_manager import DatabaseManager
from bot.settings import settings as s
from bot.database.models import RefreshToken, UserProfile

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

async def authenticate_user(username: str, password: str) -> Optional[UserProfile]:
    user_record = await DatabaseManager.fetchrow(
        "SELECT * FROM user_profiles WHERE username = $1", username
    )
    if user_record and verify_password(password, user_record["hashed_password"]):
        return UserProfile(**user_record)
    return None

def create_access_token(user: UserProfile, expires_minutes: int = 15) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=expires_minutes)
    payload = {
        "user_id": user.user_id,
        "username": user.username,
        "full_name": user.full_name,
        "exp": expire.timestamp(),
        "iat": datetime.now(UTC).timestamp(),
    }
    return jwt.encode(payload, s.JWT_SECRET_KEY, algorithm=s.JWT_ALGORITHM)

async def create_refresh_token(user: UserProfile, ip: str, user_agent: str, expires_days: int = 30) -> str:
    token = secrets.token_urlsafe(64)
    created_at = datetime.now(UTC)
    expires_at = created_at + timedelta(days=expires_days)
    await DatabaseManager.execute(
        """
        INSERT INTO refresh_tokens (user_id, token, created_at, expires_at, ip_address, user_agent)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        user.user_id, token, created_at, expires_at, ip, user_agent
    )
    return token

async def verify_refresh_token(token: str) -> Optional[RefreshToken]:
    token_record = await DatabaseManager.fetchrow(
        "SELECT * FROM refresh_tokens WHERE token = $1 AND revoked = FALSE AND expires_at > NOW()",
        token
    )
    if token_record:
        return RefreshToken(**token_record)
    return None

async def revoke_refresh_token(token: str):
    await DatabaseManager.execute(
        "UPDATE refresh_tokens SET revoked = TRUE, revoked_at = NOW() WHERE token = $1",
        token
    )
