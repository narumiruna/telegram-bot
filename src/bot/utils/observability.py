import json
import logging
from contextvars import ContextVar
from contextvars import Token
from typing import Final

import logfire

from bot.settings import settings

logger = logging.getLogger(__name__)

LOG_CONTEXT_KEYS: Final[tuple[str, ...]] = (
    "request_id",
    "update_id",
    "chat_id",
    "user_id",
    "handler",
)
DEFAULT_CONTEXT_VALUE: Final[str] = "-"
FORMAT_STR: Final[str] = (
    "%(asctime)s | %(levelname)s | %(name)s:%(lineno)d | "
    "request_id=%(request_id)s update_id=%(update_id)s chat_id=%(chat_id)s "
    "user_id=%(user_id)s handler=%(handler)s - %(message)s"
)
_LOG_CONTEXT: ContextVar[dict[str, str] | None] = ContextVar("log_context", default=None)


def get_log_context() -> dict[str, str]:
    current = _LOG_CONTEXT.get()
    if current is None:
        return {}
    return dict(current)


def bind_log_context(**fields: object) -> Token[dict[str, str] | None]:
    current = get_log_context()
    merged = dict(current)
    for key, value in fields.items():
        if value is None:
            continue
        merged[key] = str(value)
    return _LOG_CONTEXT.set(merged)


def clear_log_context(token: Token[dict[str, str] | None]) -> None:
    _LOG_CONTEXT.reset(token)


def extract_message_log_context(message: object | None) -> dict[str, str]:
    if message is None:
        return {}

    context: dict[str, str] = {}
    message_id = getattr(message, "message_id", None)
    if message_id is not None:
        context["request_id"] = f"msg:{message_id}"
    chat = getattr(message, "chat", None)
    chat_id = getattr(chat, "id", None)
    if chat_id is not None:
        context["chat_id"] = str(chat_id)
    user = getattr(message, "from_user", None)
    user_id = getattr(user, "id", None)
    if user_id is not None:
        context["user_id"] = str(user_id)
    return context


def extract_update_log_context(update: object | None) -> dict[str, str]:
    if update is None:
        return {}

    context: dict[str, str] = {}
    update_id = getattr(update, "update_id", None)
    if update_id is not None:
        context["update_id"] = str(update_id)
        context["request_id"] = f"upd:{update_id}"

    for field_name in ("message", "edited_message", "channel_post", "edited_channel_post"):
        message = getattr(update, field_name, None)
        message_context = extract_message_log_context(message)
        if message_context:
            context.update(message_context)
            break

    return context


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        current = get_log_context()
        for key in LOG_CONTEXT_KEYS:
            setattr(record, key, current.get(key, DEFAULT_CONTEXT_VALUE))
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "line": record.lineno,
            "message": record.getMessage(),
        }
        for key in LOG_CONTEXT_KEYS:
            payload[key] = getattr(record, key, DEFAULT_CONTEXT_VALUE)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def _parse_log_level() -> int:
    level_name = settings.log_level.upper()
    level = logging.getLevelName(level_name)
    if isinstance(level, int):
        return level
    logger.warning("Invalid LOG_LEVEL=%s, fallback to INFO", settings.log_level)
    return logging.INFO


def _build_formatter() -> logging.Formatter:
    if settings.log_json:
        return JsonFormatter()
    return logging.Formatter(FORMAT_STR)


def _make_console_handler(context_filter: ContextFilter) -> logging.Handler:
    handler = logging.StreamHandler()
    handler.setFormatter(_build_formatter())
    handler.addFilter(context_filter)
    return handler


def logfire_is_enabled() -> bool:
    return bool(settings.logfire_token)


def configure_logging() -> None:
    level = _parse_log_level()
    context_filter = ContextFilter()
    handlers: list[logging.Handler] = [_make_console_handler(context_filter)]
    logfire_enabled = False

    if logfire_is_enabled():
        logfire.configure(token=settings.logfire_token)
        logfire.instrument_openai_agents()
        # Note: httpx and requests instrumentation disabled to reduce noise
        # logfire.instrument_httpx()
        # logfire.instrument_requests()
        logfire.instrument_redis()
        logfire_handler = logfire.LogfireLoggingHandler()
        logfire_handler.addFilter(context_filter)
        handlers.append(logfire_handler)
        logfire_enabled = True

    logging.basicConfig(level=level, handlers=handlers, force=True)
    if logfire_enabled:
        logger.info("Logfire configured successfully.")
    else:
        logger.info("Logfire is not enabled.")
