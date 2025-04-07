from contextlib import asynccontextmanager
from datetime import (
    datetime,
    timezone,
)
import json
import logging
import re

from fastapi import (
    Body,
    Depends,
    FastAPI,
    HTTPException,
    Path,
    Request,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from jose import (
    JWTError,
    jwt,
)
from starlette.responses import JSONResponse
import uvicorn

from bot.adapters.rest.models import (
    CommandRequest,
    TextCompatibleCommandWrapper,
)
from bot.adapters.rest.rest_message import RestMessage
from bot.adapters.rest.rest_responder import RestResponder
from bot.database.database_manager import DatabaseManager
from bot.factory import create_all_factories
from bot.settings import settings as s
from bot.utils.log import get_log_level

logging.basicConfig(level=get_log_level())
logger = logging.getLogger(__name__)

command_handlers = {}
command_middlewares = {}

COMMAND_PATTERN = re.compile(r"^/?([a-zA-Z0-9_-]{1,30})\b")

@asynccontextmanager
async def lifespan(app: FastAPI):
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
        for command, handler_cls in factory.wrap_for_rest_handlers():
            command_handlers[command] = handler_cls

        for middleware in factory.create_middlewares(list(command_handlers.keys())):
            command_middlewares[middleware.__class__.__name__] = middleware

    logger.info("✅ REST command handlers and middlewares loaded.")

    yield

    logger.info("🛑 Shutting down REST API.")

app = FastAPI(lifespan=lifespan) # nresolved reference 'lifespan'


def verify_jwt_token(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())) -> json:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, s.JWT_SECRET_KEY , algorithms=[s.JWT_ALGORITHM])

        if "exp" not in payload:
            raise HTTPException(status_code=401, detail="Token has no 'exp' claim.")

        if datetime.now(timezone.utc).timestamp() > payload["exp"]:
            raise HTTPException(status_code=401, detail="Token has expired.")

        required_fields = ["user_id", "username", "full_name"]
        for field in required_fields:
            if field not in payload:
                raise HTTPException(status_code=401, detail=f"Missing '{field}' in token payload.")

        return payload

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or malformed token.")


@app.post("/{command_name}")
async def universal_command_handler(
    command_name: str = Path(..., min_length=1, max_length=30, pattern=r"^[a-zA-Z0-9_-]+$"),
    cmd: CommandRequest = Body(...),
    request: Request = None,
    user_data: dict = Depends(verify_jwt_token),
):
    text = f"/{command_name} {' '.join(cmd.args)}".strip()

    if len(text) > 1000:
        return JSONResponse({"error": "Command text too long."}, status_code=400)

    handler_cls = command_handlers.get(command_name)
    if not handler_cls:
        return JSONResponse({"error": f"Command '{command_name}' not recognized."}, status_code=404)

    message = RestMessage(TextCompatibleCommandWrapper(command_name, cmd.args), user_data)
    responder = RestResponder()
    handler_instance = handler_cls(message, responder, logger)

    executed = False

    async def invoke_once():
        nonlocal executed
        if not executed:
            executed = True
            await handler_instance.handle()
        return responder.get_response()

    for middleware in command_middlewares.values():
        response = await middleware.handle(message, responder, invoke_once)
        if response:
            return response

    return await invoke_once()



async def run_rest_api():
    config = uvicorn.Config(
        "bot.platforms.rest_runner:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
    server = uvicorn.Server(config)
    await server.serve()
