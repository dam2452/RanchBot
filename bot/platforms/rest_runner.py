from contextlib import asynccontextmanager
import logging
import re
from typing import Annotated

from fastapi import (
    APIRouter,
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
from starlette.responses import JSONResponse
import uvicorn

from bot.adapters.rest.auth.auth_service import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    revoke_all_user_refresh_tokens,
    revoke_refresh_token,
    verify_refresh_token,
)
from bot.adapters.rest.models import TextCompatibleCommandWrapper
from bot.adapters.rest.rest_message import RestMessage
from bot.adapters.rest.rest_responder import RestResponder
from bot.database import db
from bot.factory import create_all_factories
from bot.settings import settings as s
from bot.utils.constants import (
    AuthKeys,
    HttpHeaderKeys,
    JwtPayloadKeys,
)
from bot.utils.log import get_log_level

logging.basicConfig(level=get_log_level())
logger = logging.getLogger(__name__)

command_handlers = {}
COMMAND_PATTERN = re.compile(r"^/?([a-zA-Z0-9_-]{1,30})\b")

limiter = Limiter(
    key_func=get_remote_address,
    enabled=not s.DISABLE_RATE_LIMITING,
)

security = HTTPBearer()

class LoginRequest(BaseModel):
    username: Annotated[str, StringConstraints(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9._-]+$")]
    password: Annotated[str, StringConstraints(min_length=8, max_length=128)]

api_router = APIRouter()

@api_router.post("/auth/login", tags=["Authentication"])
@limiter.limit("5/minute")
async def login(data: LoginRequest, request: Request, response: Response):
    user = await authenticate_user(data.username, data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(user)
    refresh_token_value = await create_refresh_token(
        user,
        ip_address=request.client.host,
        user_agent=request.headers.get(HttpHeaderKeys.USER_AGENT),
    )

    response.set_cookie(
        AuthKeys.REFRESH_TOKEN_COOKIE,
        refresh_token_value,
        httponly=True,
        secure=s.ENVIRONMENT == "production",
        samesite="strict",
        path="/api/v1/auth",
    )
    return {AuthKeys.ACCESS_TOKEN: access_token, AuthKeys.TOKEN_TYPE: AuthKeys.BEARER}

@api_router.post("/auth/refresh", tags=["Authentication"])
@limiter.limit("5/minute")
async def refresh(request: Request, response: Response):
    refresh_token_value = request.cookies.get(AuthKeys.REFRESH_TOKEN_COOKIE)
    if not refresh_token_value:
        raise HTTPException(status_code=401, detail="No refresh token provided in cookies.")

    token_record = await verify_refresh_token(refresh_token_value)
    if not token_record:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token.")

    user_id = token_record.user_id
    user = await db.get_user_by_id(user_id)
    if not user:
        logger.warning(f"Refresh token validated for user ID {user_id}, but user not found in DB.")
        raise HTTPException(status_code=401, detail="User associated with token not found.")

    new_access_token = create_access_token(user)
    new_refresh_token_value = await create_refresh_token(
        user,
        ip_address=request.client.host,
        user_agent=request.headers.get(HttpHeaderKeys.USER_AGENT),
    )

    await revoke_refresh_token(refresh_token_value)

    response.set_cookie(
        AuthKeys.REFRESH_TOKEN_COOKIE,
        new_refresh_token_value,
        httponly=True,
        secure=s.ENVIRONMENT == "production",
        samesite="strict",
        path="/api/v1/auth",
    )
    return {AuthKeys.ACCESS_TOKEN: new_access_token, AuthKeys.TOKEN_TYPE: AuthKeys.BEARER}
@api_router.post("/auth/logout", tags=["Authentication"])
@limiter.limit("10/minute")
async def logout(request: Request, response: Response):
    refresh_token_value = request.cookies.get(AuthKeys.REFRESH_TOKEN_COOKIE)

    if not refresh_token_value:
        logger.info("Logout attempt without refresh token cookie.")
        return JSONResponse(status_code=200, content={"message": "No active session found or already logged out."})

    try:
        token_record = await verify_refresh_token(refresh_token_value)
        if token_record:
            await revoke_refresh_token(refresh_token_value)
            logger.info(f"Successfully revoked refresh token for user ID {token_record.user_id} during logout.")
        else:
            logger.info("Logout attempt with an invalid or already revoked refresh token cookie.")

    except Exception as e:
        logger.error(f"Error revoking refresh token during logout: {e}", exc_info=True)

    response.delete_cookie(
        AuthKeys.REFRESH_TOKEN_COOKIE,
        path="/api/v1/auth",
        httponly=True,
        secure=s.ENVIRONMENT == "production",
        samesite="strict",
    )

    response.status_code = 200

    json_response = JSONResponse(content={"message": "Successfully logged out."})
    response.body = json_response.body
    response.media_type = json_response.media_type

    return response

@api_router.post("/auth/logout-all", tags=["Authentication"])
@limiter.limit("5/minute")
async def logout_all(data: LoginRequest, request: Request):
    user = await authenticate_user(data.username, data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    revoked_count = await revoke_all_user_refresh_tokens(user.user_id)
    logger.info(
        f"User {user.username} (ID: {user.user_id}) revoked {revoked_count} active tokens "
        f"via logout-all from IP {request.client.host}.",
    )

    return {
        "message": f"Successfully logged out from all sessions. {revoked_count} active token(s) revoked.",
        "revoked_count": revoked_count,
    }

@api_router.post("/{command_name}", tags=["Commands"])
async def universal_handler(
    command_name: str = Path(..., regex=COMMAND_PATTERN.pattern),
    request: Request = None,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    if request is None:
        logger.error("Request object is None in universal_handler, this should not happen.")
        raise HTTPException(status_code=500, detail="Internal server error: Request object not available")

    try:
        payload = jwt.decode(
            credentials.credentials,
            s.JWT_SECRET_KEY.get_secret_value(),
            algorithms=[s.JWT_ALGORITHM],
            issuer=s.JWT_ISSUER,
            audience=s.JWT_AUDIENCE,
        )

        required_fields = {JwtPayloadKeys.USER_ID: int, JwtPayloadKeys.USERNAME: str, JwtPayloadKeys.FULL_NAME: str}
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
            raise ValueError("Invalid args list for command: must be a list of strings.")

        reply_json = request_json.get("reply_json", True)
        if not isinstance(reply_json, bool):
            raise ValueError("Invalid reply_json flag: must be boolean.")

        command_request_obj = TextCompatibleCommandWrapper(
            command_name=command_name,
            args=args,
            json=reply_json,
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve)) from ve
    except Exception as exc:
        logger.error(f"Error processing JSON payload for command '{command_name}': {exc}", exc_info=True)
        raise HTTPException(status_code=400, detail="Invalid JSON payload or request structure.") from exc

    message = RestMessage(payload=command_request_obj, user_data=payload)
    responder = RestResponder()

    handler = handler_cls(message, responder, logger)
    await handler.handle()

    return responder.get_response()


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    logger.info(f"🚀 API Startup. Rate Limiting Disabled: {s.DISABLE_RATE_LIMITING}")

    app_instance.state.limiter = limiter
    app_instance.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    await db.ensure_db_initialized()
    logger.info("DB initialization process ensured by REST runner lifespan.")

    factories = create_all_factories(logger, bot=None)
    for factory_item in factories:
        for command, handler_cls in factory_item.get_rest_handlers():
            command_handlers[command] = handler_cls
    logger.info(f"✅ REST handlers loaded by REST runner lifespan for commands: {list(command_handlers.keys())}")

    yield

    logger.info("🛑 API Shutdown logic initiated by REST runner lifespan...")
    logger.info("🛑 API Shutdown complete for REST runner.")

app = FastAPI(
    title="Ranczo Bot API v1",
    description="API for Ranczo Bot operations and commands.",
    version="1.0.0",
    lifespan=lifespan,
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
)

app.add_middleware(SlowAPIMiddleware)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    if s.ENVIRONMENT == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, proxy-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none';"
    return response

@app.get("/", tags=["Health Check"])
@limiter.limit("60/minute")
async def health_check(request: Request):
    logger.info(f"Health check endpoint requested by {request.client.host}.")
    return {"status": "ok", "message": "Welcome to the Ranchbot API!"}

app.include_router(api_router, prefix="/api/v1")

async def run_rest_api():
    config = uvicorn.Config(
        s.REST_API_APP_PATH,
        host=s.REST_API_HOST,
        port=s.REST_API_PORT,
        reload=s.ENVIRONMENT != "production",
        log_level=s.LOG_LEVEL.lower(),
    )
    server = uvicorn.Server(config)
    await server.serve()
