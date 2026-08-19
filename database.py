"""
🗄️ database.py — Lớp lưu trữ SQLite bất đồng bộ cho Ollama Telegram Bot
==========================================================================
🆕 (nâng cấp "tư duy trả lời" + "Voice"): thêm các cột persona, profile_summary,
   turns_since_summary, tts_voice vào bảng settings — tự động ALTER TABLE cho DB cũ,
   giống cách nickname đã được thêm trước đó, nên KHÔNG cần xóa/migrate DB thủ công.
"""

from __future__ import annotations

import os
import json
import asyncio
from datetime import datetime, timezone
from typing import Optional

import aiosqlite

DB_PATH = os.getenv("DB_PATH", "bot_data.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS history (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    uid     INTEGER NOT NULL,
    role    TEXT NOT NULL,
    content TEXT NOT NULL,
    ts      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_history_uid ON history(uid);

CREATE TABLE IF NOT EXISTS settings (
    uid                  INTEGER PRIMARY KEY,
    model                TEXT,
    voice_mode           TEXT DEFAULT 'smart',
    stt_engine           TEXT DEFAULT 'local',
    auto_web             INTEGER DEFAULT 0,
    media_mode           TEXT,
    nickname             TEXT,
    persona              TEXT DEFAULT 'ban_than',
    profile_summary      TEXT DEFAULT '',
    turns_since_summary  INTEGER DEFAULT 0,
    tts_voice            TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS rate_limit (
    uid       INTEGER PRIMARY KEY,
    last_ts   TEXT NOT NULL
);
"""

# 🆕 Danh sách cột có thể thiếu ở DB cũ + định nghĩa ALTER TABLE tương ứng.
# Cứ thêm tính năng mới là thêm 1 dòng ở đây — không cần xóa DB cũ để nâng cấp.
_OPTIONAL_COLUMNS = {
    "nickname": "ALTER TABLE settings ADD COLUMN nickname TEXT;",
    "persona": "ALTER TABLE settings ADD COLUMN persona TEXT DEFAULT 'ban_than';",
    "profile_summary": "ALTER TABLE settings ADD COLUMN profile_summary TEXT DEFAULT '';",
    "turns_since_summary": "ALTER TABLE settings ADD COLUMN turns_since_summary INTEGER DEFAULT 0;",
    "tts_voice": "ALTER TABLE settings ADD COLUMN tts_voice TEXT DEFAULT '';",
}

_conn: Optional[aiosqlite.Connection] = None
_lock = asyncio.Lock()


async def init_db(db_path: str = DB_PATH) -> None:
    """Khởi tạo kết nối SQLite + tạo bảng nếu chưa có. Tự động nâng cấp schema nếu thiếu cột."""
    global _conn
    _conn = await aiosqlite.connect(db_path)
    await _conn.execute("PRAGMA journal_mode = WAL;")
    await _conn.execute("PRAGMA busy_timeout = 5000;")
    await _conn.executescript(_SCHEMA)

    # Bổ sung các cột còn thiếu cho các CSDL cũ tạo trước đó (idempotent, an toàn khi chạy lại)
    async with _conn.execute("PRAGMA table_info(settings)") as cur:
        columns = [row[1] for row in await cur.fetchall()]
    for col_name, alter_sql in _OPTIONAL_COLUMNS.items():
        if col_name not in columns:
            await _conn.execute(alter_sql)

    await _conn.commit()


async def close_db() -> None:
    global _conn
    if _conn is not None:
        await _conn.close()
        _conn = None


def _require_conn() -> aiosqlite.Connection:
    if _conn is None:
        raise RuntimeError("DB chưa được khởi tạo — hãy gọi init_db() trước.")
    return _conn


# ─────────────────────────────────────────────
# 📜 History
# ─────────────────────────────────────────────
async def add_message(uid: int, role: str, content: str, max_history_pairs: int = 25) -> None:
    conn = _require_conn()
    async with _lock:
        await conn.execute(
            "INSERT INTO history (uid, role, content, ts) VALUES (?, ?, ?, ?)",
            (uid, role, content, datetime.now(timezone.utc).isoformat()),
        )
        await conn.execute(
            """
            DELETE FROM history WHERE id IN (
                SELECT id FROM history WHERE uid = ?
                ORDER BY id DESC LIMIT -1 OFFSET ?
            )
            """,
            (uid, max_history_pairs * 2),
        )
        await conn.commit()


async def get_history(uid: int) -> list[dict]:
    conn = _require_conn()
    async with conn.execute(
        "SELECT role, content FROM history WHERE uid = ? ORDER BY id ASC", (uid,)
    ) as cur:
        rows = await cur.fetchall()
    return [{"role": r[0], "content": r[1]} for r in rows]


async def get_recent_messages(uid: int, limit_pairs: int = 10) -> list[dict]:
    """🆕 Lấy N cặp tin nhắn gần nhất (dùng để tóm tắt hồ sơ trí nhớ dài hạn),
    tách riêng khỏi get_history() vì không cần lấy toàn bộ lịch sử để tóm tắt."""
    conn = _require_conn()
    async with conn.execute(
        "SELECT role, content FROM history WHERE uid = ? ORDER BY id DESC LIMIT ?",
        (uid, limit_pairs * 2),
    ) as cur:
        rows = await cur.fetchall()
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]


async def clear_history(uid: int) -> None:
    conn = _require_conn()
    async with _lock:
        await conn.execute("DELETE FROM history WHERE uid = ?", (uid,))
        await conn.commit()


# ─────────────────────────────────────────────
# ⚙️ Settings
# ─────────────────────────────────────────────
async def _ensure_settings_row(uid: int) -> None:
    conn = _require_conn()
    await conn.execute("INSERT OR IGNORE INTO settings (uid) VALUES (?)", (uid,))


async def get_settings(uid: int) -> dict:
    conn = _require_conn()
    async with conn.execute(
        "SELECT model, voice_mode, stt_engine, auto_web, media_mode, nickname, "
        "persona, profile_summary, turns_since_summary, tts_voice FROM settings WHERE uid = ?",
        (uid,),
    ) as cur:
        row = await cur.fetchone()
    if row is None:
        return {
            "model": None, "voice_mode": "smart", "stt_engine": "groq", "auto_web": False,
            "media_mode": None, "nickname": None,
            "persona": "ban_than", "profile_summary": "", "turns_since_summary": 0, "tts_voice": "",
        }
    return {
        "model": row[0],
        "voice_mode": row[1] or "smart",
        "stt_engine": row[2] or "local",
        "auto_web": bool(row[3]),
        "media_mode": row[4],
        "nickname": row[5],
        "persona": row[6] or "ban_than",
        "profile_summary": row[7] or "",
        "turns_since_summary": row[8] or 0,
        "tts_voice": row[9] or "",
    }


async def set_setting(uid: int, **fields) -> None:
    if not fields:
        return
    conn = _require_conn()
    async with _lock:
        await _ensure_settings_row(uid)
        cols = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values())
        values = [int(v) if isinstance(v, bool) else v for v in values]
        await conn.execute(f"UPDATE settings SET {cols} WHERE uid = ?", (*values, uid))
        await conn.commit()


# ─────────────────────────────────────────────
# 🧠 Trí nhớ dài hạn / Persona  (🆕)
# ─────────────────────────────────────────────
async def bump_turn_and_should_summarize(uid: int, every_n_turns: int = 10) -> bool:
    """Tăng bộ đếm lượt chat kể từ lần tóm tắt hồ sơ gần nhất; trả về True khi đã đến lúc
    tóm tắt lại (gọi summarize_for_long_term_memory() trong reasoning.py rồi lưu bằng
    set_profile_summary() để reset bộ đếm về 0)."""
    conn = _require_conn()
    async with _lock:
        await _ensure_settings_row(uid)
        await conn.execute(
            "UPDATE settings SET turns_since_summary = turns_since_summary + 1 WHERE uid = ?", (uid,)
        )
        await conn.commit()
        async with conn.execute(
            "SELECT turns_since_summary FROM settings WHERE uid = ?", (uid,)
        ) as cur:
            row = await cur.fetchone()
        return bool(row and row[0] >= every_n_turns)


async def set_profile_summary(uid: int, summary: str) -> None:
    """Lưu hồ sơ trí nhớ dài hạn mới + reset bộ đếm lượt chat về 0."""
    conn = _require_conn()
    async with _lock:
        await _ensure_settings_row(uid)
        await conn.execute(
            "UPDATE settings SET profile_summary = ?, turns_since_summary = 0 WHERE uid = ?",
            (summary, uid),
        )
        await conn.commit()


async def clear_profile(uid: int) -> None:
    """Xóa hồ sơ trí nhớ dài hạn (vd khi user muốn bot 'quên' hết, tách biệt với /reset lịch sử chat)."""
    await set_setting(uid, profile_summary="", turns_since_summary=0)


# ─────────────────────────────────────────────
# ⏱️ Rate limit
# ─────────────────────────────────────────────
async def check_and_set_rate_limit(uid: int, limit_sec: int) -> bool:
    conn = _require_conn()
    async with _lock:
        async with conn.execute("SELECT last_ts FROM rate_limit WHERE uid = ?", (uid,)) as cur:
            row = await cur.fetchone()
        now = datetime.now(timezone.utc)
        if row:
            last = datetime.fromisoformat(row[0])
            if (now - last).total_seconds() < limit_sec:
                return True
        await conn.execute(
            "INSERT INTO rate_limit (uid, last_ts) VALUES (?, ?) "
            "ON CONFLICT(uid) DO UPDATE SET last_ts = excluded.last_ts",
            (uid, now.isoformat()),
        )
        await conn.commit()
        return False