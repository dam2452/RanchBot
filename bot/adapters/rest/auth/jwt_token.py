from datetime import (
    UTC,
    datetime,
    timedelta,
)
from typing import (
    Any,
    Dict,
)

from fastapi import (
    Depends,
    HTTPException,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from jose import (
    JWTError,
    jwt,
)

from bot.settings import settings as s


def _generate_token(user_id: int, username: str, full_name: str, expire_minutes: int) -> str:
    now_utc = datetime.now(UTC)
    expire = now_utc + timedelta(minutes=expire_minutes)
    payload = {
        "user_id": user_id,
        "username": username,
        "full_name": full_name,
        "iat": now_utc.timestamp(),
        "exp": expire.timestamp(),
        "iss": s.JWT_ISSUER,
        "aud": s.JWT_AUDIENCE,
    }
    return jwt.encode(payload, s.JWT_SECRET_KEY.get_secret_value(), algorithm=s.JWT_ALGORITHM)


def _verify_jwt_token(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())) -> Dict[str, Any]:
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            s.JWT_SECRET_KEY.get_secret_value(),
            algorithms=[s.JWT_ALGORITHM],
            issuer=s.JWT_ISSUER,
            audience=s.JWT_AUDIENCE,
            options={
                "require": ["exp", "iss", "aud", "iat"],
            },
        )

        required_fields = ["user_id", "username", "full_name"]
        for field in required_fields:
            if field not in payload:
                raise HTTPException(status_code=401, detail=f"Missing '{field}' in token payload.")

        return payload

    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or malformed token.") from exc
