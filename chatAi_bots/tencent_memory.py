"""
🧠 tencent_memory.py — Client kết nối tới TencentDB Agent Memory Gateway (MemoryCore)
=======================================================================================
Thay thế cơ chế "trí nhớ dài hạn" tự chế (LLM tự tóm tắt 1 đoạn profile_summary trong
reasoning.py/database.py) bằng bộ nhớ đa tầng L0→L1→L2→L3 của dự án mã nguồn mở:
    https://github.com/TencentCloud/TencentDB-Agent-Memory

Kiến trúc:
    - L0 (conversation): lưu nguyên văn từng lượt hội thoại  -> /v3/conversation/add
    - L1 (atomic)       : các "sự thật/nguyên tử" được tự động trích xuất bởi Gateway
                          (chạy nền, dùng LLM cấu hình ở TDAI_LLM_*)   -> /v3/atomic/search
    - L2 (scenario) / L3 (core-persona): hồ sơ/kịch bản được nén dần theo thời gian
                          -> /v3/core/read (đọc persona đã chưng cất, không cần bot tự tóm tắt)

Bot KHÔNG cần tự gọi Ollama để tóm tắt hồ sơ nữa — Gateway tự làm việc đó ở nền dựa trên
LLM cấu hình (có thể trỏ về endpoint OpenAI-compatible của chính Ollama, xem README).

Toàn bộ lỗi kết nối tới Gateway đều được nuốt (log warning) và bot vẫn hoạt động bình
thường bằng lịch sử SQLite hiện có — Memory Gateway là lớp tăng cường, không phải điểm
lỗi (fail open).
"""

from __future__ import annotations

import os
from typing import Optional

import httpx

from bot_logger import logger

# ── Cấu hình (đọc trực tiếp từ env, giữ tách biệt với config.py để module này
#    có thể bật/tắt độc lập mà không phá vỡ các bot không dùng tính năng này) ──
MEMORY_ENABLED   = os.getenv("MEMORY_TENCENTDB_ENABLED", "false").lower() == "true"
MEMORY_BASE_URL  = os.getenv("MEMORY_TENCENTDB_ENDPOINT", "http://127.0.0.1:8420")
MEMORY_API_KEY   = os.getenv("MEMORY_TENCENTDB_API_KEY", "")
MEMORY_SERVICE_ID = os.getenv("MEMORY_TENCENTDB_SERVICE_ID", "default")
MEMORY_AGENT_ID  = os.getenv("MEMORY_TENCENTDB_AGENT_ID", "telegram-bot")
MEMORY_TEAM_ID   = os.getenv("MEMORY_TENCENTDB_TEAM_ID", "default")
MEMORY_TIMEOUT   = float(os.getenv("MEMORY_TENCENTDB_TIMEOUT_SEC", "8"))
MEMORY_RECALL_LIMIT = int(os.getenv("MEMORY_TENCENTDB_RECALL_LIMIT", "5"))


def _headers() -> dict:
    headers = {
        "Content-Type": "application/json",
        "x-tdai-service-id": MEMORY_SERVICE_ID,
        "x-tdai-agent-id": MEMORY_AGENT_ID,
        "x-tdai-team-id": MEMORY_TEAM_ID,
    }
    if MEMORY_API_KEY:
        headers["Authorization"] = f"Bearer {MEMORY_API_KEY}"
    return headers


def _session_id(uid: int) -> str:
    """Mỗi user Telegram = 1 session cố định (khớp iso theo user_id ở tầng L1+)."""
    return f"tg-{uid}"


async def _post(path: str, uid: int, payload: dict) -> Optional[dict]:
    if not MEMORY_ENABLED:
        return None
    payload = {**payload, "user_id": str(uid)}
    url = f"{MEMORY_BASE_URL.rstrip('/')}{path}"
    try:
        async with httpx.AsyncClient(timeout=MEMORY_TIMEOUT) as client:
            resp = await client.post(url, headers=_headers(), json=payload)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.warning(f"⚠️ [tencent_memory] Gọi {path} thất bại (bot vẫn chạy bình thường): {e}")
        return None


# ─────────────────────────────────────────────
# ✍️ Ghi hội thoại vào L0 (gọi nền, không chặn phản hồi cho user)
# ─────────────────────────────────────────────
async def add_turn(uid: int, role: str, content: str) -> None:
    """Đẩy 1 lượt chat (user hoặc assistant) lên Gateway. Gateway sẽ tự động lên lịch
    trích xuất L1 (atomic facts) ở nền sau mỗi vài lượt — không cần bot tự gọi LLM tóm tắt."""
    if not MEMORY_ENABLED or not content:
        return
    await _post(
        "/v3/conversation/add",
        uid,
        {
            "session_id": _session_id(uid),
            "messages": [{"role": role, "content": content}],
        },
    )


# ─────────────────────────────────────────────
# 🔎 Truy hồi trí nhớ liên quan (L1 atomic) trước khi trả lời
# ─────────────────────────────────────────────
async def recall(uid: int, query: str, limit: int = MEMORY_RECALL_LIMIT) -> str:
    """Tìm các 'ký ức nguyên tử' (sở thích, sự kiện, quyết định...) liên quan tới câu hỏi
    hiện tại, xuyên suốt mọi session của user này (không giới hạn theo session_id).
    Trả về đoạn text đã format sẵn, dùng thay cho `profile_summary` cũ."""
    if not MEMORY_ENABLED or not query:
        return ""
    data = await _post("/v3/atomic/search", uid, {"query": query, "limit": limit})
    if not data:
        return ""
    results = (data.get("data") or {}).get("results") or data.get("results") or []
    if not results:
        return ""
    lines = [f"- {r.get('content', '').strip()}" for r in results if r.get("content")]
    return "\n".join(lines)


async def read_persona(uid: int) -> str:
    """Đọc hồ sơ người dùng đã được chưng cất ở tầng L3 (core/persona) — tương đương
    'profile_summary' cũ nhưng do Gateway tự xây dựng và cập nhật dần theo thời gian."""
    if not MEMORY_ENABLED:
        return ""
    data = await _post("/v3/core/read", uid, {})
    if not data:
        return ""
    content = (data.get("data") or {}).get("content") or data.get("content") or ""
    return content.strip()


async def get_memory_context(uid: int, query: str) -> str:
    """Gộp persona (L3) + các ký ức liên quan tới câu hỏi hiện tại (L1) thành 1 khối
    context duy nhất, dùng làm giá trị truyền vào tham số `profile_summary` sẵn có của
    llm_engine.build_grounded_messages() — KHÔNG cần sửa llm_engine.py."""
    if not MEMORY_ENABLED:
        return ""
    persona, atoms = "", ""
    try:
        persona = await read_persona(uid)
        atoms = await recall(uid, query)
    except Exception as e:
        logger.warning(f"⚠️ [tencent_memory] Lỗi truy hồi trí nhớ: {e}")
    parts = []
    if persona:
        parts.append(f"[Hồ sơ người dùng]\n{persona}")
    if atoms:
        parts.append(f"[Ký ức liên quan tới câu hỏi hiện tại]\n{atoms}")
    return "\n\n".join(parts)
