import json
import logging
import re

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
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

from bot.adapters.rest.models import CommandRequest
from bot.adapters.rest.rest_message import RestMessage
from bot.adapters.rest.rest_responder import RestResponder
from bot.database.database_manager import DatabaseManager
from bot.factory import create_all_factories
from bot.settings import settings
from bot.utils.log import get_log_level

logging.basicConfig(level=get_log_level())
logger = logging.getLogger(__name__)

app = FastAPI()

command_handlers = {}
command_middlewares = {}

security = HTTPBearer()
SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM


def verify_jwt_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> json:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        required_fields = ["user_id", "username", "full_name"]
        if not all(field in payload for field in required_fields):
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


@app.on_event("startup")
async def startup():
    await DatabaseManager.init_pool(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        database=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        schema=settings.POSTGRES_SCHEMA,
    )
    await DatabaseManager.init_db()

    factories = create_all_factories(logger, bot=None)

    for factory in factories:
        for command, handler_cls in factory.wrap_for_rest_handlers():
            command_handlers[command] = handler_cls

        for middleware in factory.create_middlewares(list(command_handlers.keys())):
            command_middlewares[middleware.__class__.__name__] = middleware

    logger.info("✅ REST command handlers and middlewares loaded.")


@app.post("/command")
async def handle_command(
    cmd: CommandRequest,
    request: Request,
    user_data: dict = Depends(verify_jwt_token),
):
    message = RestMessage(cmd, user_data)
    responder = RestResponder()

    match = re.match(r"/?(\w+)", cmd.text.strip())
    command = match.group(1) if match else None

    if not command:
        return JSONResponse({"error": "Command not found in text."}, status_code=400)

    handler_cls = command_handlers.get(command)
    if not handler_cls:
        return JSONResponse({"error": f"Command '{command}' not recognized."}, status_code=404)

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
    config = uvicorn.Config("bot.platforms.rest_runner:app", host="0.0.0.0", port=8000, reload=True)
    server = uvicorn.Server(config)
    await server.serve()
