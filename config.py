"""
config.py — Nạp toàn bộ biến môi trường & hằng số dùng chung cho bot.
Import đây thay vì đọc os.getenv() rải rác ở mọi file.
"""

from __future__ import annotations

import os
import re
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


def _require_env(name: str) -> str:
    val = os.getenv(name, "")
    if not val:
        raise RuntimeError(
            f"❌ Thiếu biến môi trường bắt buộc: {name}. "
            f"Hãy tạo file .env (xem .env.example) và điền giá trị thật."
        )
    return val


# ── Telegram & Ollama ──────────────────────────────────────────────────────────
TELEGRAM_TOKEN   = _require_env("TELEGRAM_TOKEN")
OLLAMA_BASE_URL  = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_MODEL    = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
OLLAMA_TIMEOUT_SEC    = int(os.getenv("OLLAMA_TIMEOUT_SEC", "120"))
OLLAMA_RETRY_ATTEMPTS = int(os.getenv("OLLAMA_RETRY_ATTEMPTS", "2"))

# ── Access control ────────────────────────────────────────────────────────────
ALLOWED_USERS  = os.getenv("ALLOWED_USERS", "")
ADMIN_USER_IDS = os.getenv("ADMIN_USER_IDS", "")
ALLOWED_IDS: set[int] = {int(x) for x in ALLOWED_USERS.split(",") if x.strip()} if ALLOWED_USERS else set()
ADMIN_IDS:   set[int] = {int(x) for x in ADMIN_USER_IDS.split(",") if x.strip()} if ADMIN_USER_IDS else set()

# ── Feature flags ─────────────────────────────────────────────────────────────
MAX_HISTORY    = int(os.getenv("MAX_HISTORY", "25"))
RATE_LIMIT_SEC = int(os.getenv("RATE_LIMIT_SEC", "3"))
MAX_UPLOAD_MB  = float(os.getenv("MAX_UPLOAD_MB", "15"))
REQUIRE_MENTION_IN_GROUPS = os.getenv("REQUIRE_MENTION_IN_GROUPS", "true").lower() != "false"
LONG_TERM_MEMORY_EVERY_N_TURNS = int(os.getenv("LONG_TERM_MEMORY_EVERY_N_TURNS", "10"))
STREAM_EDIT_INTERVAL = float(os.getenv("STREAM_EDIT_INTERVAL", "0.7"))

# ── Paths ─────────────────────────────────────────────────────────────────────
DB_PATH  = os.getenv("DB_PATH", "data/bot_data.db")
LOG_FILE = os.getenv("LOG_FILE", "logs/bot.log")

# ── Optional API keys ─────────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# ── Tesseract ─────────────────────────────────────────────────────────────────
TESSERACT_CMD = os.getenv("TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
OCR_LANG      = os.getenv("OCR_LANG", "eng+vie")

# ── Weather ───────────────────────────────────────────────────────────────────
CITY_COORDS: dict[str, tuple[float, float]] = {
    "hà nội":    (21.0285, 105.8542),
    "hồ chí minh": (10.8231, 106.6297),
    "đà nẵng":   (16.0544, 108.2022),
}

WMO_CODE: dict[int, str] = {
    0: "☀️ Trời quang đãng", 1: "🌤️ Ít mây", 2: "⛅ Mây rải rác", 3: "☁️ Trời nhiều mây",
    45: "🌫️ Có sương mù", 48: "🌫️ Sương mù đọng nước băng",
    51: "🌧️ Mưa phùn nhẹ", 53: "🌧️ Mưa phùn vừa", 55: "🌧️ Mưa phùn dày đặc",
    61: "🌧️ Mưa nhẹ", 63: "🌧️ Mưa vừa", 65: "🌧️ Mưa to",
    71: "❄️ Tuyết rơi nhẹ", 73: "❄️ Tuyết rơi vừa", 75: "❄️ Tuyết rơi dày",
    80: "🌦️ Mưa rào nhẹ", 81: "🌦️ Mưa rào vừa", 82: "⛈️ Mưa rào rất to",
    95: "⛈️ Dông bão",
}

# ── News sources ──────────────────────────────────────────────────────────────
NEWS_FEEDS: dict[str, tuple[str, str]] = {
    "vnexpress":     ("VnExpress",      "https://vnexpress.net/rss/tin-moi-nhat.rss"),
    "tuoitre":       ("Tuổi Trẻ",       "https://tuoitre.vn/home.rss"),
    "thanhnien":     ("Thanh Niên",     "https://thanhnien.vn/rss/home.rss"),
    "dantri":        ("Dân Trí",        "https://dantri.com.vn/rss/home.rss"),
    "bbcvietnamese": ("BBC Tiếng Việt", "https://feeds.bbci.co.uk/vietnamese/rss.xml"),
}

# ── Web search trigger keywords ───────────────────────────────────────────────
WEB_SEARCH_TRIGGER_KEYWORDS_STRONG = [
    "giá vàng", "tỷ giá", "giá xăng", "giá dầu", "giá bitcoin", "giá coin", "lãi suất", "giá cổ phiếu",
    "tổng thống", "thủ tướng", "chủ tịch nước", "bộ trưởng", "ceo", "tổng giám đốc",
    "hlv trưởng", "huấn luyện viên trưởng", "đương nhiệm",
    "kết quả", "vô địch", "tỷ số", "bầu cử", "world cup", "olympic", "sea games",
    "mới nhất", "cập nhật", "tin tức",
]
WEB_SEARCH_TRIGGER_KEYWORDS_WEAK = [
    "bây giờ", "hôm nay", "hiện tại", "hiện nay", "gần đây", "vừa qua", "vừa rồi",
    "tuần này", "tháng này", "năm nay", "chủ tịch", "là ai",
]
WEB_SEARCH_TRIGGER_KEYWORDS = WEB_SEARCH_TRIGGER_KEYWORDS_STRONG + WEB_SEARCH_TRIGGER_KEYWORDS_WEAK

_QUESTION_HINT_RE = re.compile(
    r"[?？]\s*$|\b(là gì|là ai|bao nhiêu|thế nào|ra sao|khi nào|ở đâu|vì sao|tại sao|có phải|đúng không)\b",
    re.IGNORECASE,
)

COMPARISON_TRIGGER_KEYWORDS = [
    "so sánh", "khác nhau", "khác biệt", " vs ", " vs.", "so với", "hơn hay", "hơn kém",
    "ưu nhược điểm", "ưu điểm nhược điểm", "nên chọn", "nên mua", "cái nào tốt hơn", "loại nào",
]


def should_trigger_web_search(text: str) -> bool:
    """Quyết định có nên tự động tra web hay không, dựa trên từ khóa mạnh/yếu + dấu hiệu câu hỏi."""
    low = text.lower()
    if any(kw in low for kw in WEB_SEARCH_TRIGGER_KEYWORDS_STRONG):
        return True
    if any(kw in low for kw in WEB_SEARCH_TRIGGER_KEYWORDS_WEAK):
        return bool(_QUESTION_HINT_RE.search(low))
    return False


def aqi_label(pm25: float | None) -> str:
    if pm25 is None:
        return "Không có dữ liệu"
    if pm25 <= 12:    return "🟢 Tốt"
    if pm25 <= 35.4:  return "🟡 Trung bình"
    if pm25 <= 55.4:  return "🟠 Kém (nhóm nhạy cảm nên hạn chế ra ngoài)"
    if pm25 <= 150.4: return "🔴 Xấu"
    return "🟣 Rất xấu — hạn chế ra ngoài"
