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
import reasoning
from bot_logger import logger
from config import LONG_TERM_MEMORY_EVERY_N_TURNS
from llm_engine import chat_with_llm
from skills.voice import transcribe_for_user, maybe_send_voice_reply
from skills.web_search import raw_search_data, format_web_context, format_sources_footer
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
    if auto_web:
        await update.effective_chat.send_action(ChatAction.TYPING)
        try:
            raw_data = await raw_search_data(transcribed_text)
            if raw_data:
                web_context = format_web_context(raw_data)
                sources_footer = format_sources_footer(raw_data)
        except Exception as e:
            logger.warning(f"⚠️ Lỗi tìm kiếm web (voice): {e}")

    complexity = reasoning.classify_complexity(transcribed_text)
    length_hint = {
        "simple":  "CỰC KỲ NGẮN GỌN (1 câu, tối đa 20 từ)",
        "medium":  "NGẮN GỌN (2-3 câu, tối đa 60 từ)",
        "complex": "ĐẦY ĐỦ Ý nhưng vẫn súc tích (4-6 câu, tối đa 120 từ)",
    }[complexity]

    history = await db.get_history(uid)
    voice_msgs = history.copy()
    if voice_msgs:
        last_usr = voice_msgs[-1]["content"]
        voice_msgs[-1] = dict(voice_msgs[-1])
        voice_msgs[-1]["content"] = (
            f"{last_usr}\n\n"
            "⚠️ YÊU CẦU ĐẶC BIỆT DÀNH CHO VOICE:\n"
            f"Người dùng đang nghe qua giọng nói (TTS). Hãy trả lời {length_hint}, "
            "đi thẳng vào câu trả lời/kết quả chính, nói tự nhiên như đang nói chuyện thật "
            "(KHÔNG dùng markdown/bảng, KHÔNG đọc toàn bộ thông tin cào được)."
        )

    reply = await chat_with_llm(
        voice_msgs, model, web_context, force_concise=True,
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
