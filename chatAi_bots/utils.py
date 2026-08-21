"""
utils.py — Tiện ích dùng chung: kiểm tra quyền, split message, safe_reply,
           group mention, rate limit, lock per user, history helpers.
"""

from __future__ import annotations

import asyncio
import re
from typing import Optional

from telegram import Update
from telegram.constants import ChatType

import database as db
from config import (
    ALLOWED_IDS, ADMIN_IDS, RATE_LIMIT_SEC, MAX_HISTORY, REQUIRE_MENTION_IN_GROUPS,
)

# ── Runtime state (module-level singletons) ────────────────────────────────────
BOT_USERNAME: Optional[str] = None                     # set trong post_init
ACTIVE_GEN_TASKS: dict[int, asyncio.Task] = {}         # uid -> Task đang sinh câu trả lời
_USER_GEN_LOCKS:  dict[int, asyncio.Lock] = {}         # uid -> Lock tuần tự hóa


def get_user_lock(uid: int) -> asyncio.Lock:
    lock = _USER_GEN_LOCKS.get(uid)
    if lock is None:
        lock = asyncio.Lock()
        _USER_GEN_LOCKS[uid] = lock
    return lock


# ── Access control ─────────────────────────────────────────────────────────────
def is_allowed(uid: int) -> bool:
    return not ALLOWED_IDS or uid in ALLOWED_IDS


def is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS


async def is_rate_limited(uid: int) -> bool:
    return await db.check_and_set_rate_limit(uid, RATE_LIMIT_SEC)


# ── Group chat helpers ─────────────────────────────────────────────────────────
def is_addressed_in_group(update: Update) -> bool:
    chat = update.effective_chat
    if chat is None or chat.type == ChatType.PRIVATE:
        return True
    if not REQUIRE_MENTION_IN_GROUPS:
        return True
    msg = update.effective_message
    if msg is None:
        return False
    text = msg.text or msg.caption or ""
    if BOT_USERNAME and f"@{BOT_USERNAME.lower()}" in text.lower():
        return True
    reply_to = msg.reply_to_message
    if reply_to and reply_to.from_user and reply_to.from_user.username and BOT_USERNAME:
        if reply_to.from_user.username.lower() == BOT_USERNAME.lower():
            return True
    return False


def strip_mention(text: str) -> str:
    if BOT_USERNAME:
        text = re.sub(rf"@{re.escape(BOT_USERNAME)}", "", text, flags=re.IGNORECASE)
    return text.strip()


# ── Message helpers ────────────────────────────────────────────────────────────
def split_message(text: str, max_len: int = 4000) -> list[str]:
    if len(text) <= max_len:
        return [text]
    parts, cur = [], ""
    for line in text.splitlines(keepends=True):
        if len(cur) + len(line) > max_len:
            parts.append(cur)
            cur = ""
        cur += line
    if cur:
        parts.append(cur)
    return parts


async def safe_reply(update: Update, text: str, **kwargs):
    target = update.callback_query.message if update.callback_query else update.message
    for chunk in split_message(text):
        try:
            await target.reply_text(chunk, parse_mode="Markdown",
                                    disable_web_page_preview=True, **kwargs)
        except Exception:
            await target.reply_text(chunk)


async def notify_rate_limited(update: Update):
    try:
        await safe_reply(update, f"⏳ Bạn thao tác hơi nhanh — đợi khoảng {RATE_LIMIT_SEC}s rồi gửi lại nhé.")
    except Exception:
        pass


# ── User settings shortcuts ────────────────────────────────────────────────────
from config import DEFAULT_MODEL   # noqa: E402  (after db import to avoid circular)


async def get_user_model(uid: int) -> str:
    s = await db.get_settings(uid)
    return s["model"] or DEFAULT_MODEL


async def get_auto_web_mode(uid: int) -> bool:
    return (await db.get_settings(uid))["auto_web"]


async def get_media_mode(uid: int) -> Optional[str]:
    return (await db.get_settings(uid))["media_mode"]


async def get_user_nickname(uid: int) -> Optional[str]:
    return (await db.get_settings(uid))["nickname"]


async def add_to_history(uid: int, role: str, content: str):
    await db.add_message(uid, role, content, max_history_pairs=MAX_HISTORY)
