"""Middleware que registra interacciones: chat_id, usuario, comando y tiempo de respuesta."""
import logging
import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

logger = logging.getLogger(__name__)

MAX_LOG_TEXT_LEN = 200


def _user_info(msg: Message) -> str:
    if not msg.from_user:
        return "unknown"
    u = msg.from_user
    parts = [f"id={u.id}"]
    if u.username:
        parts.append(f"@{u.username}")
    if u.first_name:
        parts.append(u.first_name)
    return " ".join(parts)


def _command_or_text(msg: Message) -> str:
    text = (msg.text or msg.caption or "").strip()
    if not text:
        return "(empty)"
    if text.startswith("/"):
        return text.split(maxsplit=1)[0]
    if len(text) <= MAX_LOG_TEXT_LEN:
        return text
    return text[:MAX_LOG_TEXT_LEN] + "..."


class InteractionLoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)

        msg = event
        chat_id = msg.chat.id
        user_str = _user_info(msg)
        cmd_or_text = _command_or_text(msg)
        started = time.perf_counter()

        logger.info(
            "user_interaction chat_id=%s user=%s command_or_text=%s",
            chat_id,
            user_str,
            cmd_or_text[:MAX_LOG_TEXT_LEN] if len(cmd_or_text) > MAX_LOG_TEXT_LEN else cmd_or_text,
        )

        def _short_label() -> str:
            if not cmd_or_text or not cmd_or_text.strip():
                return "msg"
            if cmd_or_text.startswith("/"):
                parts = cmd_or_text.split(maxsplit=1)
                return parts[0] if parts else "cmd"
            return "text"

        try:
            result = await handler(event, data)
            elapsed = time.perf_counter() - started
            logger.info(
                "handler_done chat_id=%s command_or_text=%s elapsed_sec=%.2f",
                chat_id,
                _short_label(),
                elapsed,
            )
            return result
        except Exception as e:
            elapsed = time.perf_counter() - started
            logger.warning(
                "handler_error chat_id=%s command_or_text=%s elapsed_sec=%.2f error=%s",
                chat_id,
                _short_label(),
                elapsed,
                e,
            )
            raise
