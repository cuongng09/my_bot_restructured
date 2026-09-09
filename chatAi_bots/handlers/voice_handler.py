"""
handlers/voice_handler.py — Nhận voice note → STT → LLM → TTS reply.
"""

from __future__ import annotations

import asyncio
import tempfile
from typing import Optional

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

import database as db
from bot_logger import logger
from config import LONG_TERM_MEMORY_EVERY_N_TURNS, should_trigger_web_search
from llm_engine import chat_with_llm, decide_web_search
from skills.voice import transcribe_for_user, maybe_send_voice_reply
from skills.web_search import raw_search_data, format_web_context, format_sources_footer, clean_search_query
from handlers.text_handler import _update_long_term_memory
from utils import (
    is_allowed, is_addressed_in_group, is_rate_limited, notify_rate_limited,
    safe_reply, get_user_lock, ACTIVE_GEN_TASKS,
    add_to_history, get_auto_web_mode, get_user_model,
)


async def _process_voice_reply(
    update: Update,
    uid: int,
    transcribed_text: str,
    model: str,
    nickname: Optional[str],
    persona: Optional[str],
    profile_summary: str,
) -> str:
    """Tìm web (nếu cần) + gọi LLM không-stream (tối ưu cho voice — concise)."""
    web_context, sources_footer = "", ""
    auto_web = await get_auto_web_mode(uid)
    try:
        if auto_web:
            decision = await decide_web_search(transcribed_text, model)
            need_search = decision.get("need_search", False)
            search_query = decision.get("query", "").strip()
        else:
            need_search = should_trigger_web_search(transcribed_text)
            search_query = clean_search_query(transcribed_text) if need_search else ""

        if need_search and search_query:
            await update.effective_chat.send_action(ChatAction.TYPING)
            raw_data = await raw_search_data(search_query)
            if raw_data:
                web_context = format_web_context(raw_data)
                sources_footer = format_sources_footer(raw_data)
            else:
                logger.info(f"🌐 Không tìm thấy kết quả web cho '{search_query}' (voice), fallback sang LLM.")
    except Exception as e:
        logger.warning(f"⚠️ Lỗi tìm kiếm web (voice): {e}")

    history = await db.get_history(uid)
    reply = await chat_with_llm(
        history, model, web_context, force_concise=False,
        nickname=nickname, persona=persona, profile_summary=profile_summary,
    )
    if sources_footer:
        reply += sources_footer
    return reply


async def handle_voice(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_allowed(uid) or not is_addressed_in_group(update):
        return
    if await is_rate_limited(uid):
        return await notify_rate_limited(update)

    voice = update.message.voice or update.message.audio
    file  = await ctx.bot.get_file(voice.file_id)

    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        ogg_path = tmp.name
    await file.download_to_drive(ogg_path)

    transcribed = await transcribe_for_user(uid, ogg_path)
    if not transcribed or transcribed.startswith("["):
        return await safe_reply(update, transcribed)

    await safe_reply(update, f"🎙️ *Nghe được:* `{transcribed}`")

    model    = await get_user_model(uid)
    settings = await db.get_settings(uid)
    nickname        = settings["nickname"]
    persona         = settings["persona"]
    profile_summary = settings["profile_summary"]

    await add_to_history(uid, "user", transcribed)

    async with get_user_lock(uid):
        task = asyncio.create_task(_process_voice_reply(
            update, uid, transcribed, model, nickname, persona, profile_summary,
        ))
        ACTIVE_GEN_TASKS[uid] = task
        try:
            reply = await task
        except asyncio.CancelledError:
            await safe_reply(update, "⏹️ *Đã dừng theo yêu cầu /stop*")
            return
        finally:
            ACTIVE_GEN_TASKS.pop(uid, None)

    await add_to_history(uid, "assistant", reply)

    should_summarize = await db.bump_turn_and_should_summarize(
        uid, every_n_turns=LONG_TERM_MEMORY_EVERY_N_TURNS
    )
    if should_summarize:
        asyncio.create_task(_update_long_term_memory(uid, model))

    await update.effective_chat.send_action(ChatAction.TYPING)
    await safe_reply(update, reply)
    await maybe_send_voice_reply(update, uid, reply)