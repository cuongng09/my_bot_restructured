"""Text-only Telegram conversation pipeline."""

from __future__ import annotations

import asyncio
from typing import Optional

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from my_bot.config import LONG_TERM_MEMORY_EVERY_N_TURNS, STREAM_EDIT_INTERVAL
from my_bot.core import database as db, reasoning
from my_bot.core.llm_engine import (
    chat_with_llm, chat_with_llm_stream, clean_model_generated_sources,
    decide_web_search,
)
from my_bot.core.logger import logger
from my_bot.core.utils import (
    ACTIVE_GEN_TASKS, add_to_history, get_user_lock, get_user_model,
    is_addressed_in_group, is_allowed, is_rate_limited, notify_rate_limited,
    safe_reply, split_message, strip_mention,
)
from my_bot.skills.web_search import (
    clean_search_query, format_sources_footer, format_web_context,
    raw_search_data,
)


async def _update_long_term_memory(uid: int, model: str) -> None:
    try:
        settings = await db.get_settings(uid)
        summary = await reasoning.summarize_for_long_term_memory(
            chat_with_llm, model, await db.get_recent_messages(uid, 10),
            settings["profile_summary"],
        )
        if summary:
            await db.set_profile_summary(uid, summary)
    except Exception as exc:
        logger.warning("Long-term memory update failed: %s", exc)


async def _stream_reply(
    update: Update,
    messages: list[dict],
    model: str,
    web_context: str,
    nickname: Optional[str],
    persona: str,
    profile_summary: str,
    sources_footer: str,
) -> str:
    placeholder = await update.message.reply_text("⏳ ...")
    visible_text = ""
    stream_filter = reasoning.ThinkingStreamFilter()
    loop = asyncio.get_running_loop()
    last_edit = loop.time()
    try:
        async for piece in chat_with_llm_stream(
            messages, model, web_context, bool(web_context), nickname, persona,
            profile_summary,
        ):
            visible = stream_filter.feed(piece)
            if not visible:
                continue
            visible_text += visible
            if loop.time() - last_edit >= STREAM_EDIT_INTERVAL and len(visible_text) <= 3900:
                try:
                    await placeholder.edit_text(visible_text + " ▌")
                except Exception:
                    pass
                last_edit = loop.time()
    except asyncio.CancelledError:
        visible_text += stream_filter.flush()
        visible_text = clean_model_generated_sources(visible_text)
        await _edit_final(placeholder, visible_text + "\n\n⏹️ _(đã dừng theo yêu cầu /stop)_")
        return visible_text

    visible_text = clean_model_generated_sources(visible_text + stream_filter.flush())
    await _edit_final(placeholder, visible_text + sources_footer)
    if len(visible_text + sources_footer) > 4000:
        for chunk in split_message((visible_text + sources_footer)[4000:]):
            await safe_reply(update, chunk)
    return visible_text


async def _edit_final(message, text: str) -> None:
    text = text or "⚠️ Không nhận được phản hồi từ Ollama."
    try:
        await message.edit_text(text[:4000], parse_mode="Markdown")
    except Exception:
        await message.edit_text(text[:4000])


async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    if not is_allowed(uid) or not is_addressed_in_group(update):
        return
    if await is_rate_limited(uid):
        return await notify_rate_limited(update)

    text = strip_mention((update.message.text or "").strip())
    if not text:
        return
    await update.effective_chat.send_action(ChatAction.TYPING)

    settings = await db.get_settings(uid)
    model = await get_user_model(uid)
    web_context = ""
    sources_footer = ""
    if settings["auto_web"]:
        try:
            decision = await decide_web_search(text, model)
            query = clean_search_query(decision.get("query", text))
            if decision.get("need_search") and query:
                results = await raw_search_data(query)
                web_context = format_web_context(results) if results else ""
                sources_footer = format_sources_footer(results) if results else ""
        except Exception as exc:
            logger.warning("Web search failed: %s", exc)

    await add_to_history(uid, "user", text)
    history = await db.get_history(uid)
    if reasoning.classify_complexity(text) == "complex":
        history = [*history]
        history[-1] = {
            **history[-1],
            "content": reasoning.wrap_with_hidden_reasoning(history[-1]["content"]),
        }

    async with get_user_lock(uid):
        task = asyncio.create_task(_stream_reply(
            update, history, model, web_context, settings["nickname"],
            settings["persona"], settings["profile_summary"], sources_footer,
        ))
        ACTIVE_GEN_TASKS[uid] = task
        try:
            reply = await task
        finally:
            ACTIVE_GEN_TASKS.pop(uid, None)

    await add_to_history(uid, "assistant", reply)
    if await db.bump_turn_and_should_summarize(uid, LONG_TERM_MEMORY_EVERY_N_TURNS):
        asyncio.create_task(_update_long_term_memory(uid, model))
