"""
bot_logger.py — Khởi tạo logging tập trung: console + file xoay vòng (rotating).
Import logger từ đây thay vì tự tạo trong mỗi module.
"""

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
