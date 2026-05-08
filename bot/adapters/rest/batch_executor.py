import json
import logging
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Type,
)

from bot.adapters.rest.models import (
    BatchCommandItem,
    TextCompatibleCommandWrapper,
)
from bot.adapters.rest.rest_message import RestMessage
from bot.adapters.rest.rest_responder import RestResponder
from bot.handlers.bot_message_handler import BotMessageHandler


async def execute_batch(
    *,
    commands: List[BatchCommandItem],
    jwt_payload: Dict[str, Any],
    command_handlers: Dict[str, Type[BotMessageHandler]],
    middleware_adapter,
    logger: logging.Logger,
) -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []

    for i, cmd in enumerate(commands):
        handler_cls = command_handlers.get(cmd.command)
        if not handler_cls:
            results.append(_error_result(cmd.command, i, f"Unknown command '{cmd.command}'"))
            continue

        wrapper = TextCompatibleCommandWrapper(
            command_name=cmd.command,
            args=cmd.args,
            json=cmd.reply_json,
        )
        message = RestMessage(payload=wrapper, user_data=jwt_payload)
        responder = RestResponder(prefer_json=cmd.reply_json)
        handler = handler_cls(message, responder, logger)

        async def _run_handler(_h=handler) -> None:
            await _h.handle()

        try:
            if middleware_adapter:
                await middleware_adapter.execute(message, responder, _run_handler)
            else:
                await _run_handler()

            raw_response = responder.get_response()
            response_body = _deserialize_response(raw_response)

            results.append({
                "command": cmd.command,
                "index": i,
                "status": "success",
                "response": response_body,
            })
        except Exception as exc:
            logger.error(f"Batch command '{cmd.command}' (index {i}) failed: {exc}", exc_info=True)
            results.append(_error_result(cmd.command, i, str(exc)))

    succeeded = sum(1 for r in results if r["status"] == "success")
    return {
        "results": results,
        "summary": {
            "total": len(results),
            "succeeded": succeeded,
            "failed": len(results) - succeeded,
        },
    }


def _error_result(command: str, index: int, error: str) -> Dict[str, Any]:
    return {
        "command": command,
        "index": index,
        "status": "error",
        "error": error,
    }


def _deserialize_response(response) -> Optional[Any]:
    if hasattr(response, "body"):
        return json.loads(response.body)
    return None
