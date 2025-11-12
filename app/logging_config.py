"""
Logging configuration module with security features.
Handles log file storage, rotation, and sensitive data sanitization.
Provides standardized logging functions for consistent log format.
"""

import json
import logging
import logging.handlers
import re
from datetime import datetime
from pathlib import Path


def sanitize_phone(phone: str | None) -> str:
    """
    Sanitize phone number for logging.
    Example: +380123456789 -> +380****6789
    """
    if not phone:
        return "[NO_PHONE]"

    digits = re.sub(r"[^\d+]", "", phone)

    if len(digits) < 4:
        return "[INVALID_PHONE]"

    if digits.startswith("+"):
        prefix = digits[:4]
        suffix = digits[-4:]
        return f"{prefix}****{suffix}"
    else:
        prefix = digits[:3]
        suffix = digits[-4:]
        return f"{prefix}****{suffix}"


def sanitize_name(name: str | None) -> str:
    """
    Sanitize name for logging - show only first letter and length.
    Example: "John" -> "J*** (4 chars)"
    """
    if not name:
        return "[NO_NAME]"

    if len(name) <= 1:
        return "[SHORT_NAME]"

    first_char = name[0]
    length = len(name)
    return f"{first_char}*** ({length} chars)"


def sanitize_text(text: str | None, max_length: int = 50) -> str:
    """
    Sanitize text for logging - truncate if too long.
    """
    if not text:
        return "[EMPTY]"

    if len(text) <= max_length:
        return text

    return f"{text[:max_length]}... (truncated, {len(text)} chars)"


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }

        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "username"):
            log_data["username"] = record.username
        if hasattr(record, "action"):
            log_data["action"] = record.action
        if hasattr(record, "data"):
            log_data["data"] = record.data

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


def setup_logging(log_dir: str = "logs", log_level: int = logging.INFO) -> None:
    """
    Set up logging configuration with file handler and console handler.
    Uses structured JSON format for file logs and readable format for console.

    Args:
        log_dir: Directory to store log files
        log_level: Logging level (default: INFO)
    """
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    root_logger.handlers.clear()

    structured_formatter = StructuredFormatter()

    console_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(module)s.%(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_path / "bot.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(structured_formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(console_formatter)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)


def get_user_info(message_or_callback) -> dict:
    """
    Extract safe user information for logging.
    Works with both Message and CallbackQuery objects.
    Returns user_id (int or None), username (str or None).

    Priority for CallbackQuery:
    1. callback.from_user (user who pressed the button)
    2. callback.message.from_user (fallback if callback.from_user is None)

    Args:
        message_or_callback: Message or CallbackQuery object

    Returns:
        dict with user_id and username (both can be None)
    """
    user_id = None
    username = None
    user = None

    # Check if it's a CallbackQuery (has both 'from_user' and 'message' attributes)
    if hasattr(message_or_callback, "message") and hasattr(message_or_callback, "from_user"):
        # This is a CallbackQuery - prioritize callback.from_user (the user who clicked)
        if message_or_callback.from_user:
            user = message_or_callback.from_user
        # Fallback to message.from_user if callback.from_user is not available
        elif message_or_callback.message and message_or_callback.message.from_user:
            user = message_or_callback.message.from_user

    # Handle Message object (only has from_user, no message attribute)
    elif hasattr(message_or_callback, "from_user") and not hasattr(message_or_callback, "message"):
        user = message_or_callback.from_user

    # Extract user_id and username
    if user:
        user_id = user.id
        username = user.username if user.username else None

    return {
        "user_id": user_id,
        "username": username,
    }


def log_info(
    logger: logging.Logger,
    action: str,
    user_id: int | None = None,
    username: str | None = None,
    **kwargs,
) -> None:
    """
    Standardized INFO log function.

    Args:
        logger: Logger instance
        action: Action description (e.g., "user_started_bot", "data_collected")
        user_id: User ID (optional)
        username: Username (optional)
        **kwargs: Additional data to log
    """
    extra = {
        "action": action,
        "user_id": user_id,
        "username": username,
    }
    if kwargs:
        extra["data"] = kwargs

    logger.info(f"ACTION: {action}", extra=extra)


def log_warning(
    logger: logging.Logger,
    action: str,
    reason: str,
    user_id: int | None = None,
    username: str | None = None,
    **kwargs,
) -> None:
    """
    Standardized WARNING log function.

    Args:
        logger: Logger instance
        action: Action description (e.g., "validation_failed", "invalid_input")
        reason: Reason for warning
        user_id: User ID (optional)
        username: Username (optional)
        **kwargs: Additional data to log
    """
    extra = {
        "action": action,
        "user_id": user_id,
        "username": username,
    }
    if kwargs:
        extra["data"] = kwargs

    logger.warning(f"WARNING: {action} | REASON: {reason}", extra=extra)


def log_error(
    logger: logging.Logger,
    action: str,
    error: str,
    user_id: int | None = None,
    username: str | None = None,
    exc_info: bool = False,
    **kwargs,
) -> None:
    """
    Standardized ERROR log function.

    Args:
        logger: Logger instance
        action: Action description (e.g., "processing_failed", "exception_occurred")
        error: Error message
        user_id: User ID (optional)
        username: Username (optional)
        exc_info: Include exception info (default: False)
        **kwargs: Additional data to log
    """
    extra = {
        "action": action,
        "user_id": user_id,
        "username": username,
    }
    if kwargs:
        extra["data"] = kwargs

    logger.error(f"ERROR: {action} | ERROR: {error}", extra=extra, exc_info=exc_info)
