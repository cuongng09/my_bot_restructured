"""
handlers/text_handler.py — Xử lý tin nhắn văn bản: streaming, web search, hidden reasoning,
                            long-term memory update.
"""

from __future__ import annotations

import asyncio
from typing import Optional

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

import database as db
import reasoning
from bot_logger import logger
from config import LONG_TERM_MEMORY_EVERY_N_TURNS, STREAM_EDIT_INTERVAL, should_trigger_web_search
from llm_engine import chat_with_llm, chat_with_llm_stream
from skills.web_search import raw_search_data, format_web_context, format_sources_footer
from utils import (
    is_allowed, is_addressed_in_group, is_rate_limited,
    notify_rate_limited, strip_mention, safe_reply, split_message,
    get_user_lock, ACTIVE_GEN_TASKS,
    add_to_history, get_auto_web_mode, get_media_mode, get_user_model,
)
from skills.ocr import perform_translation


async def _update_long_term_memory(uid: int, model: str):
    """Tóm tắt lịch sử gần đây + hồ sơ cũ thành hồ sơ mới (nền, không chặn phản hồi)."""
    try:
        recent = await db.get_recent_messages(uid, limit_pairs=10)
        old_summary = (await db.get_settings(uid))["profile_summary"]
        new_summary = await reasoning.summarize_for_long_term_memory(
            chat_with_llm, model, recent, old_summary
        )
        if new_summary:
            await db.set_profile_summary(uid, new_summary)
    except Exception as e:
        logger.warning(f"⚠️ Lỗi tóm tắt hồ sơ trí nhớ dài hạn: {e}")


async def _stream_reply(
    update: Update,
    messages: list[dict],
    model: str,
    web_context: str,
    force_concise: bool,
    nickname: Optional[str],
    sources_footer: str = "",
    persona: Optional[str] = None,
    profile_summary: str = "",
) -> str:
    """Gửi placeholder rồi edit dần theo stream. Trả về full_text cuối cùng.
    Hỗ trợ /stop cancel và lọc phần suy luận ẩn <suy_nghi>."""
    placeholder = await update.message.reply_text("⏳ ...")
    buffer, full_text = "", ""
    loop = asyncio.get_event_loop()
    last_edit = loop.time()
    think_filter = reasoning.ThinkingStreamFilter()

    try:
        async for piece in chat_with_llm_stream(
            messages, model, web_context, force_concise, nickname, persona, profile_summary
        ):
            visible = think_filter.feed(piece)
            if not visible:
                continue
            buffer += visible
            full_text += visible
            now = loop.time()
            if now - last_edit >= STREAM_EDIT_INTERVAL and len(full_text) <= 3900:
                try:
                    await placeholder.edit_text(full_text + " ▌")
                except Exception:
                    pass
                last_edit = now
    except asyncio.CancelledError:
        full_text += think_filter.flush()
        full_text += "\n\n⏹️ _(đã dừng theo yêu cầu /stop)_"
        if sources_footer:
            full_text += sources_footer
        try:
            await placeholder.edit_text(full_text[:4000], parse_mode="Markdown")
        except Exception:
            try:
                await placeholder.edit_text(full_text[:4000])
            except Exception:
                pass
        return full_text

    full_text += think_filter.flush()

    if sources_footer and full_text:
        full_text += sources_footer

    first_chunk = full_text[:4000] if full_text else "⚠️ (không có phản hồi)"
    try:
        await placeholder.edit_text(first_chunk, parse_mode="Markdown")
    except Exception:
        try:
            await placeholder.edit_text(first_chunk)
        except Exception:
            pass

    if len(full_text) > 4000:
        for chunk in split_message(full_text[4000:]):
            await safe_reply(update, chunk)

    return full_text


async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_allowed(uid) or not is_addressed_in_group(update):
        return
    if await is_rate_limited(uid):
        return await notify_rate_limited(update)

    text = strip_mention(update.message.text.strip())
    if not text:
        return

    # Chế độ dịch văn bản (kích hoạt từ dashboard)
    mode = await get_media_mode(uid)
    if mode in ["text_trans_en_vi", "text_trans_vi_en"]:
        await update.effective_chat.send_action(ChatAction.TYPING)
        reply = perform_translation(text, mode.replace("text_", "vision_"))
        await db.set_setting(uid, media_mode=None)
        return await safe_reply(update, f"🔤 **Bản dịch Google:**\n\n{reply}")

    await update.effective_chat.send_action(ChatAction.TYPING)
    web_context, force_concise, sources_footer = "", False, ""
    try:
        auto_web = await get_auto_web_mode(uid)
        if auto_web or should_trigger_web_search(text):
            raw_data = await raw_search_data(text)
            if raw_data:
                web_context = format_web_context(raw_data)
                sources_footer = format_sources_footer(raw_data)
                force_concise = True
    except Exception as e:
        logger.warning(f"⚠️ Lỗi tìm kiếm web: {e}")

    settings = await db.get_settings(uid)
    nickname = settings["nickname"]
    persona, profile_summary = settings["persona"], settings["profile_summary"]

    await add_to_history(uid, "user", text)
    history = await db.get_history(uid)
    model = await get_user_model(uid)

    # Hidden reasoning cho câu hỏi phức tạp
    complexity = reasoning.classify_complexity(text)
    if complexity == "complex":
        history = history.copy()
        last = dict(history[-1])
        last["content"] = reasoning.wrap_with_hidden_reasoning(last["content"])
        history[-1] = last

    async with get_user_lock(uid):
        task = asyncio.create_task(_stream_reply(
            update, history, model, web_context, force_concise, nickname,
            sources_footer, persona=persona, profile_summary=profile_summary,
        ))
        ACTIVE_GEN_TASKS[uid] = task
        try:
            reply = await task
        finally:
            ACTIVE_GEN_TASKS.pop(uid, None)

    await add_to_history(uid, "assistant", reply)

    should_summarize = await db.bump_turn_and_should_summarize(uid, every_n_turns=LONG_TERM_MEMORY_EVERY_N_TURNS)
    if should_summarize:
        asyncio.create_task(_update_long_term_memory(uid, model))
