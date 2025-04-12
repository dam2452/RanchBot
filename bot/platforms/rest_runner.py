from contextlib import asynccontextmanager
import logging
import re
from typing import Annotated

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Path,
    Request,
    Response,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from jose import (
    JWTError,
    jwt,
)
from pydantic import (
    BaseModel,
    StringConstraints,
)
from slowapi import (
    Limiter,
    _rate_limit_exceeded_handler,
)
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
import uvicorn

from bot.adapters.rest.auth.auth_service import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    revoke_refresh_token,
    verify_refresh_token,
)
from bot.adapters.rest.models import TextCompatibleCommandWrapper
from bot.adapters.rest.rest_message import RestMessage
from bot.adapters.rest.rest_responder import RestResponder
from bot.database.database_manager import DatabaseManager
from bot.factory import create_all_factories
from bot.settings import settings as s
from bot.utils.log import get_log_level

logging.basicConfig(level=get_log_level())
logger = logging.getLogger(__name__)

command_handlers = {}

COMMAND_PATTERN = re.compile(r"^/?([a-zA-Z0-9_-]{1,30})\b")

limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    app_instance.state.limiter = limiter
    app_instance.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    logger.info("🌐 Initializing DB connection...")
    await DatabaseManager.init_pool(
        host=s.POSTGRES_HOST,
        port=s.POSTGRES_PORT,
        database=s.POSTGRES_DB,
        user=s.POSTGRES_USER,
        password=s.POSTGRES_PASSWORD,
        schema=s.POSTGRES_SCHEMA,
    )
    await DatabaseManager.init_db()
    factories = create_all_factories(logger, bot=None)
    for factory in factories:
        for command, handler_cls in factory.get_rest_handlers():
            command_handlers[command] = handler_cls
    logger.info("✅ REST handlers loaded.")
    yield
    logger.info("🛑 API Shutdown.")

app = FastAPI(lifespan=lifespan)
app.add_middleware(SlowAPIMiddleware)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"

    response.headers["Content-Security-Policy"] = "default-src 'none'"

    return response

class LoginRequest(BaseModel):
    username: Annotated[str, StringConstraints(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9._-]+$")]
    password: Annotated[str, StringConstraints(min_length=8, max_length=128)]


@app.post("/auth/login")
@limiter.limit("5/minute")
async def login(data: LoginRequest, request: Request, response: Response):
    user = await authenticate_user(data.username, data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(user)
    refresh_token = await create_refresh_token(
        user,
        ip_address=request.client.host,
        user_agent=request.headers.get('User-Agent'),
    )

    response.set_cookie(
        "refresh_token",
        refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        path="/",
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/auth/refresh")
@limiter.limit("5/minute")
async def refresh(request: Request, response: Response):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")

    token_record = await verify_refresh_token(refresh_token)
    if not token_record:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = await DatabaseManager.get_user_by_id(token_record.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_access_token = create_access_token(user)
    new_refresh_token = await create_refresh_token(
        user,
        ip_address=request.client.host,
        user_agent=request.headers.get('User-Agent'),
    )

    await revoke_refresh_token(refresh_token)

    response.set_cookie(
        "refresh_token",
        new_refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        path="/",
    )
    return {"access_token": new_access_token, "token_type": "bearer"}

security = HTTPBearer()

@app.post("/{command_name}")
async def universal_handler(
    command_name: str = Path(..., regex=COMMAND_PATTERN.pattern),
    request: Request = None,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    try:
        payload = jwt.decode(
            credentials.credentials,
            s.JWT_SECRET_KEY,
            algorithms=[s.JWT_ALGORITHM],
            issuer=s.JWT_ISSUER,
            audience=s.JWT_AUDIENCE,
        )

        required_fields = {"user_id": int, "username": str, "full_name": str}
        for field, expected_type in required_fields.items():
            if field not in payload or not isinstance(payload[field], expected_type):
                raise HTTPException(status_code=401, detail=f"Invalid payload field: {field}")

    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc

    handler_cls = command_handlers.get(command_name)
    if not handler_cls:
        raise HTTPException(status_code=404, detail=f"Unknown command '{command_name}'")

    try:
        request_json = await request.json()
        args = request_json.get("args", [])
        if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
            raise ValueError("Invalid args list")

        reply_json = request_json.get("reply_json", False)
        if not isinstance(reply_json, bool):
            raise ValueError("Invalid reply_json flag")

        command_request = TextCompatibleCommandWrapper(
            command_name=command_name,
            args=args,
            json=reply_json,
        )

    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    message = RestMessage(payload=command_request, user_data=payload)
    responder = RestResponder()

    handler = handler_cls(message, responder, logger)
    await handler.handle()

    return responder.get_response()


async def run_rest_api():
    config = uvicorn.Config(
        s.REST_API_APP_PATH,
        host=s.REST_API_HOST,
        port=s.REST_API_PORT,
        reload=False,
    )
    server = uvicorn.Server(config)

    await server.serve()
