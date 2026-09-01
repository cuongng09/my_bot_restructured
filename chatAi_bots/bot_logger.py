"""
bot_logger.py — Khởi tạo logging tập trung: console + file xoay vòng (rotating).
Import logger từ đây thay vì tự tạo trong mỗi module.
"""

import asyncio
import logging
import logging.handlers

from config import LOG_FILE

logger = logging.getLogger("my_bot")
logger.setLevel(logging.INFO)

_fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

_console = logging.StreamHandler()
_console.setFormatter(_fmt)
logger.addHandler(_console)

try:
    _file = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    _file.setFormatter(_fmt)
    logger.addHandler(_file)
except Exception as e:
    logger.warning(f"⚠️ Không thể tạo file log '{LOG_FILE}': {e}")

logging.getLogger("httpx").setLevel(logging.WARNING)


def record_status_event(user_id, chat_id, module: str, duration_ms: int | float, error_code: str = "OK") -> None:
    """Ghi sự kiện hoạt động theo mẫu user_id, chat_id, module, duration, error_code."""
    try:
        from database import log_user_chat_status
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(log_user_chat_status(user_id, chat_id, module, duration_ms, error_code))
            return
        loop.create_task(log_user_chat_status(user_id, chat_id, module, duration_ms, error_code))
    except Exception:
        logger.warning(
            "⚠️ Không ghi được user/chat status log: user_id=%s chat_id=%s module=%s duration_ms=%s error_code=%s",
            user_id,
            chat_id,
            module,
            duration_ms,
            error_code,
            exc_info=True,
        )
