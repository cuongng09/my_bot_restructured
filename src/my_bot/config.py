"""Single source of truth for text-only bot configuration."""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv

load_dotenv()


def _require_env(name: str) -> str:
    value = os.getenv(name, "")
    if not value and not (
        name == "TELEGRAM_TOKEN"
        and os.getenv("RUNNING_WEBAPP", "").lower() in {"1", "true", "yes"}
    ):
        raise RuntimeError(f"Thiếu biến môi trường bắt buộc: {name}")
    return value


TELEGRAM_TOKEN = _require_env("TELEGRAM_TOKEN")
TELEGRAM_CONNECT_TIMEOUT = float(os.getenv("TELEGRAM_CONNECT_TIMEOUT", "15"))
TELEGRAM_READ_TIMEOUT = float(os.getenv("TELEGRAM_READ_TIMEOUT", "30"))

_ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
if os.getenv("RUNNING_IN_DOCKER") and any(host in _ollama_url for host in ("localhost", "127.0.0.1")):
    _ollama_url = re.sub(r"localhost|127\.0\.0\.1", "host.docker.internal", _ollama_url)
OLLAMA_BASE_URL = _ollama_url
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
OLLAMA_TIMEOUT_SEC = int(os.getenv("OLLAMA_TIMEOUT_SEC", "240"))
OLLAMA_RETRY_ATTEMPTS = int(os.getenv("OLLAMA_RETRY_ATTEMPTS", "2"))
OLLAMA_CONTEXT_SIZE = int(os.getenv("OLLAMA_CONTEXT_SIZE", "8192"))

ALLOWED_USERS = os.getenv("ALLOWED_USERS", "")
ADMIN_USER_IDS = os.getenv("ADMIN_USER_IDS", "")
ALLOWED_IDS = {int(value) for value in ALLOWED_USERS.split(",") if value.strip()}
ADMIN_IDS = {int(value) for value in ADMIN_USER_IDS.split(",") if value.strip()}

MAX_HISTORY = int(os.getenv("MAX_HISTORY", "25"))
RATE_LIMIT_SEC = int(os.getenv("RATE_LIMIT_SEC", "3"))
REQUIRE_MENTION_IN_GROUPS = os.getenv("REQUIRE_MENTION_IN_GROUPS", "true").lower() != "false"
LONG_TERM_MEMORY_EVERY_N_TURNS = int(os.getenv("LONG_TERM_MEMORY_EVERY_N_TURNS", "10"))
STREAM_EDIT_INTERVAL = float(os.getenv("STREAM_EDIT_INTERVAL", "0.7"))

DB_PATH = os.getenv("DB_PATH", "data/bot_data.db")
LOG_FILE = os.getenv("LOG_FILE", "logs/bot.log")
SEARXNG_URL = os.getenv("SEARXNG_URL", "http://127.0.0.1:8081").rstrip("/")
SEARCH_CACHE_TTL_SEC = int(os.getenv("SEARCH_CACHE_TTL_SEC", "3600"))
TRUSTED_DOMAINS = os.getenv("TRUSTED_DOMAINS", "")
TRUSTED_DOMAINS_ONLY = os.getenv("TRUSTED_DOMAINS_ONLY", "false").lower() in {"1", "true", "yes"}
LOW_VALUE_SCRAPE_DOMAINS = os.getenv("LOW_VALUE_SCRAPE_DOMAINS", "")

WEBAPP_HOST = os.getenv("WEBAPP_HOST", "0.0.0.0")
WEBAPP_PORT = int(os.getenv("WEBAPP_PORT", "8080"))
WEBAPP_TOKEN = os.getenv("WEBAPP_TOKEN", "")
WEBAPP_PUBLIC_URL = os.getenv("WEBAPP_PUBLIC_URL", "")

CITY_COORDS = {
    "hà nội": (21.0285, 105.8544),
    "hồ chí minh": (10.8231, 106.6297),
    "đà nẵng": (16.0544, 108.2022),
}
WMO_CODE = {
    0: "☀️ Trời quang đãng", 1: "🌤️ Ít mây", 2: "⛅ Mây rải rác", 3: "☁️ Nhiều mây",
    45: "🌫️ Sương mù", 51: "🌧️ Mưa phùn", 61: "🌧️ Mưa nhẹ",
    63: "🌧️ Mưa vừa", 65: "🌧️ Mưa to", 80: "🌦️ Mưa rào", 95: "⛈️ Dông bão",
}
NEWS_FEEDS = {
    "vnexpress": ("VnExpress", "https://vnexpress.net/rss/tin-moi-nhat.rss"),
    "tuoitre": ("Tuổi Trẻ", "https://tuoitre.vn/home.rss"),
    "thanhnien": ("Thanh Niên", "https://thanhnien.vn/rss/home.rss"),
    "dantri": ("Dân Trí", "https://dantri.com.vn/rss/home.rss"),
    "bbcvietnamese": ("BBC Tiếng Việt", "https://feeds.bbci.co.uk/vietnamese/rss.xml"),
}

WEB_SEARCH_TRIGGER_KEYWORDS_STRONG = (
    "hôm nay", "hiện nay", "mới nhất", "giá", "tin tức", "thời tiết",
    "tỷ giá", "bitcoin", "crypto", "so sánh", "theo nguồn",
)
COMPARISON_TRIGGER_KEYWORDS = ("so sánh", "khác nhau", "nên chọn", "ưu nhược điểm")


def should_trigger_web_search(text: str) -> bool:
    normalized = text.lower().strip()
    if len(normalized.split()) <= 6 and normalized in {"chào", "hello", "hi", "cảm ơn", "ok"}:
        return False
    return any(keyword in normalized for keyword in WEB_SEARCH_TRIGGER_KEYWORDS_STRONG)


def get_vietnam_time_str() -> str:
    return datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M:%S GMT+7")


def aqi_label(value: int) -> str:
    if value <= 50:
        return "Tốt"
    if value <= 100:
        return "Trung bình"
    if value <= 150:
        return "Kém"
    return "Xấu"
