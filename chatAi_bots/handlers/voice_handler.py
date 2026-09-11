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
    """Tìm web thông minh mặc định + gọi LLM không-stream."""
    web_context, sources_footer = "", ""
    try:
        decision = await decide_web_search(transcribed_text, model)
        need_search = decision.get("need_search", False)
        search_query = decision.get("query", "").strip()

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
    from llm_engine import clean_model_generated_sources
    reply = clean_model_generated_sources(reply)
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

    # Tách câu đầu trọng tâm để phản hồi voice siêu nhanh
    from skills.document_exporter import split_core_and_detail, export_document_smart, has_tabular_or_detailed_content
    core_summary, _ = split_core_and_detail(reply)

    await update.effective_chat.send_action(ChatAction.TYPING)

    # Hiển thị text: ngắn gọn khi dài/chi tiết (tương tự text_handler)
    check = has_tabular_or_detailed_content(reply)
    is_long_detail = check.get("has_table") or check.get("is_detailed")
    if is_long_detail:
        text_to_show = f"{core_summary}\n\n📄 *Thông tin chi tiết được đính kèm trong tệp bên dưới:* 📎"
    else:
        text_to_show = reply
    await safe_reply(update, text_to_show)

    # Tự động xuất tệp Excel (.xlsx) hoặc Word (.docx) nếu có bảng số liệu hoặc phân tích chi tiết
    try:
        export_result = export_document_smart(transcribed, reply, summary=core_summary)
        if export_result:
            file_path, file_type = export_result
            with open(file_path, "rb") as doc_file:
                caption = (
                    f"📊 *Thông tin chi tiết ({file_type})*\n"
                    f"Tệp đã được định dạng chuẩn, không bị vỡ bảng hay lỗi font."
                )
                await update.effective_chat.send_document(
                    document=doc_file,
                    caption=caption,
                    parse_mode="Markdown",
                )
    except Exception as exp_err:
        logger.warning(f"⚠️ Lỗi gửi tệp đính kèm trong voice_handler: {exp_err}")

    # Voice reply: CHỈ ĐỌC CÂU ĐẦU TRỌNG TÂM (core_summary)
    # Giảm thời gian phát từ hàng chục giây xuống 2-5s, không đọc bảng biểu hay URL!
    await maybe_send_voice_reply(update, uid, core_summary)