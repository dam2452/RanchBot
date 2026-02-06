from unittest.mock import (
    AsyncMock,
    MagicMock,
)

import pytest

from bot.handlers.not_sending_videos.serial_context_handler import SerialContextHandler


@pytest.mark.asyncio
async def test_show_current_series():
    message = MagicMock()
    message.get_text.return_value = "/serial"
    message.get_user_id.return_value = 123
    message.should_reply_json.return_value = False

    responder = AsyncMock()
    logger = MagicMock()

    handler = SerialContextHandler(message, responder, logger)
    handler.serial_manager.get_user_active_series = AsyncMock(return_value="ranczo")
    handler.serial_manager.list_available_series = AsyncMock(return_value=["ranczo", "kiepscy"])

    await handler._do_handle()

    responder.send_markdown.assert_called_once()
    call_args = responder.send_markdown.call_args[0][0]
    assert "ranczo" in call_args.lower()


@pytest.mark.asyncio
async def test_change_series_valid(db_pool):
    message = MagicMock()
    message.get_text.return_value = "/serial kiepscy"
    message.get_user_id.return_value = 123
    message.should_reply_json.return_value = False

    responder = AsyncMock()
    logger = MagicMock()

    handler = SerialContextHandler(message, responder, logger)
    handler.serial_manager.list_available_series = AsyncMock(return_value=["ranczo", "kiepscy"])
    handler.serial_manager.set_user_active_series = AsyncMock()

    await handler._do_handle()

    handler.serial_manager.set_user_active_series.assert_called_once_with(123, "kiepscy")


@pytest.mark.asyncio
async def test_change_series_invalid():
    message = MagicMock()
    message.get_text.return_value = "/serial nonexistent"
    message.get_user_id.return_value = 123
    message.should_reply_json.return_value = False

    responder = AsyncMock()
    logger = MagicMock()

    handler = SerialContextHandler(message, responder, logger)
    handler.serial_manager.list_available_series = AsyncMock(return_value=["ranczo"])

    await handler._do_handle()

    responder.send_markdown.assert_called_once()
    call_args = responder.send_markdown.call_args[0][0]
    assert "nieznany" in call_args.lower() or "dostępne" in call_args.lower()
