from contextlib import asynccontextmanager
import logging

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
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
from pydantic import BaseModel
import uvicorn

from bot.adapters.rest.auth.auth_service import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    revoke_refresh_token,
    verify_refresh_token,
)
from bot.database.database_manager import DatabaseManager
from bot.factory import create_all_factories
from bot.settings import settings as s
from bot.utils.log import get_log_level

logging.basicConfig(level=get_log_level())
logger = logging.getLogger(__name__)

command_handlers = {}

@asynccontextmanager
async def lifespan(_: FastAPI):
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


class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/auth/login")
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
        "refresh_token", refresh_token,
        httponly=True, secure=True, samesite="strict",
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/auth/refresh")
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
        "refresh_token", new_refresh_token,
        httponly=True, secure=True, samesite="strict",
    )
    return {"access_token": new_access_token, "token_type": "bearer"}

security = HTTPBearer()

@app.post("/{command_name}")
async def universal_handler(
    command_name: str,
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    try:
        payload = jwt.decode(
            credentials.credentials,
            s.JWT_SECRET_KEY,
            algorithms=[s.JWT_ALGORITHM],
        )
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc

    handler_cls = command_handlers.get(command_name)
    if not handler_cls:
        raise HTTPException(404, f"Unknown command '{command_name}'")

    handler = handler_cls(payload, request)
    return await handler.handle()

def run_rest_api():
    uvicorn.run(
        s.REST_API_APP_PATH,
        host=s.REST_API_HOST,
        port=s.REST_API_PORT,
        reload=False,
    )

if __name__ == "__main__":
    run_rest_api()
