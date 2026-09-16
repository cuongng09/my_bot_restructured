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

from core import database as db
from core import reasoning
from core.logger import logger
from config import LONG_TERM_MEMORY_EVERY_N_TURNS, STREAM_EDIT_INTERVAL, should_trigger_web_search
from core.llm_engine import chat_with_llm, chat_with_llm_stream, decide_web_search
from skills.web_search import raw_search_data, format_web_context, format_sources_footer, clean_search_query
from core.utils import (
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
            if now - last_edit >= STREAM_EDIT_INTERVAL:
                from skills.document_exporter import split_core_and_detail, has_tabular_or_detailed_content
                c_check = has_tabular_or_detailed_content(full_text)
                if c_check.get("has_table") or (c_check.get("is_detailed") and len(full_text) > 500):
                    core_part, _ = split_core_and_detail(full_text)
                    preview = f"{core_part}\n\n⏳ *Đang xử lý nội dung chi tiết vào tệp tài liệu...* ▌"
                    try:
                        await placeholder.edit_text(preview, parse_mode="Markdown")
                    except Exception:
                        pass
                elif len(full_text) <= 3900:
                    try:
                        await placeholder.edit_text(full_text + " ▌")
                    except Exception:
                        pass
                last_edit = now
    except asyncio.CancelledError:
        from llm_engine import clean_model_generated_sources
        from skills.document_exporter import split_core_and_detail, has_tabular_or_detailed_content
        full_text += think_filter.flush()
        full_text = clean_model_generated_sources(full_text)
        stop_note = "\n\n⏹️ _(đã dừng theo yêu cầu /stop)_"
        check = has_tabular_or_detailed_content(full_text)
        is_long_detail = check.get("has_table") or check.get("is_detailed")
        if is_long_detail:
            core_summary, _ = split_core_and_detail(full_text)
            display_text = f"{core_summary}{stop_note}"
            if sources_footer:
                display_text += sources_footer
        else:
            display_text = full_text + stop_note + (sources_footer or "")
        try:
            await placeholder.edit_text(display_text[:4000], parse_mode="Markdown")
        except Exception:
            try:
                await placeholder.edit_text(display_text[:4000])
            except Exception:
                pass
        return full_text

    full_text += think_filter.flush()
    from llm_engine import clean_model_generated_sources
    from skills.document_exporter import split_core_and_detail, has_tabular_or_detailed_content
    full_text = clean_model_generated_sources(full_text)

    # Quyết định hiển thị: câu đầu trọng tâm + chi tiết vào file Word / Excel
    check = has_tabular_or_detailed_content(full_text)
    is_long_detail = check.get("has_table") or check.get("is_detailed")

    if is_long_detail:
        core_summary, _ = split_core_and_detail(full_text)
        file_hint = "\n\n📄 *Thông tin chi tiết được đính kèm trong tệp bên dưới:* 📎"
        display_text = core_summary + file_hint
        if sources_footer:
            display_text += sources_footer
    else:
        display_text = full_text
        if sources_footer:
            display_text += sources_footer

    first_chunk = display_text[:4000] if display_text else "⚠️ (không có phản hồi)"
    try:
        await placeholder.edit_text(first_chunk, parse_mode="Markdown")
    except Exception:
        try:
            await placeholder.edit_text(first_chunk)
        except Exception:
            pass

    if len(display_text) > 4000:
        for chunk in split_message(display_text[4000:]):
            await safe_reply(update, chunk)

    return full_text  # Luôn trả full_text để exporter dùng


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

    settings = await db.get_settings(uid)
    nickname = settings["nickname"]
    persona, profile_summary = settings["persona"], settings["profile_summary"]
    model = await get_user_model(uid)

    web_context, force_concise, sources_footer = "", False, ""
    try:
        # Chế độ Tìm kiếm thông minh đa tầng MẶC ĐỊNH cho toàn bộ tin nhắn:
        # 1. Lọc nhanh chào hỏi/code/toán không cần search
        # 2. LLM phân tích thời sự/công nghệ/thực tế và trích xuất search query tối ưu
        # 3. SearXNG -> DDGS -> HTML cào sâu -> RAG
        decision = await decide_web_search(text, model)
        need_search = decision.get("need_search", False)
        search_query = decision.get("query", "").strip()

        if need_search and search_query:
            raw_data = await raw_search_data(search_query)
            if raw_data:
                web_context = format_web_context(raw_data)
                sources_footer = format_sources_footer(raw_data)
                force_concise = True
            else:
                logger.info(f"🌐 Không tìm thấy kết quả web cho '{search_query}', fallback sang tri thức bách khoa của AI.")
    except Exception as e:
        logger.warning(f"⚠️ Lỗi tìm kiếm web: {e}")

    await add_to_history(uid, "user", text)
    history = await db.get_history(uid)

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

    # Tự động xuất tệp Excel (.xlsx) hoặc Word (.docx) nếu có bảng số liệu hoặc phân tích chi tiết
    try:
        from skills.document_exporter import export_document_smart, split_core_and_detail
        core_sum, _ = split_core_and_detail(reply)
        export_result = export_document_smart(text, reply, summary=core_sum)
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
        logger.warning(f"⚠️ Lỗi gửi tệp đính kèm: {exp_err}")

    should_summarize = await db.bump_turn_and_should_summarize(uid, every_n_turns=LONG_TERM_MEMORY_EVERY_N_TURNS)
    if should_summarize:
        asyncio.create_task(_update_long_term_memory(uid, model))