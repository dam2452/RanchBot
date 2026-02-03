import pytest
from unittest.mock import AsyncMock, MagicMock
from bot.handlers.not_sending_videos.serial_context_handler import SerialContextHandler


@pytest.mark.asyncio
async def test_show_current_series():
    message = MagicMock()
    message.get_text.return_value = "/serial"
    message.get_user_id.return_value = 123

    responder = AsyncMock()
    logger = MagicMock()

    handler = SerialContextHandler(message, responder, logger)
    handler.serial_manager.get_user_active_series = AsyncMock(return_value="ranczo")

    await handler._do_handle()

    responder.send_text.assert_called_once()
    call_args = responder.send_text.call_args[0][0]
    assert "ranczo" in call_args.lower()


@pytest.mark.asyncio
async def test_change_series_valid():
    message = MagicMock()
    message.get_text.return_value = "/serial kiepscy"
    message.get_user_id.return_value = 123

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

    responder = AsyncMock()
    logger = MagicMock()

    handler = SerialContextHandler(message, responder, logger)
    handler.serial_manager.list_available_series = AsyncMock(return_value=["ranczo"])

    await handler._do_handle()

    responder.send_text.assert_called_once()
    call_args = responder.send_text.call_args[0][0]
    assert "invalid" in call_args.lower() or "available" in call_args.lower()
