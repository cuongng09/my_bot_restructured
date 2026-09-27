"""Text-only Telegram dashboard."""

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from my_bot.config import WEBAPP_PUBLIC_URL
from my_bot.core import database as db, reasoning
from my_bot.core.llm_engine import get_ollama_models
from my_bot.core.utils import get_user_model, is_admin, is_allowed, safe_reply


def _back() -> InlineKeyboardButton:
    return InlineKeyboardButton("⬅️ Trạm chính", callback_data="menu_main")


async def _render_main(uid: int) -> tuple[str, InlineKeyboardMarkup]:
    settings = await db.get_settings(uid)
    models = await get_ollama_models()
    persona = reasoning.PERSONAS.get(settings["persona"], reasoning.PERSONAS[reasoning.DEFAULT_PERSONA])
    rows = [
        [InlineKeyboardButton(f"🦙 Mô hình: {settings['model'] or '(mặc định)'}", callback_data="menu_model")],
        [InlineKeyboardButton(f"🎭 Persona: {persona['label']}", callback_data="menu_persona")],
        [InlineKeyboardButton(
            f"🌐 Tìm web: {'bật' if settings['auto_web'] else 'tắt'}",
            callback_data="toggle_autoweb",
        )],
        [InlineKeyboardButton("❓ Trợ giúp", callback_data="menu_help")],
    ]
    if is_admin(uid) and WEBAPP_PUBLIC_URL:
        rows.append([InlineKeyboardButton("🌐 Mở WebApp", url=WEBAPP_PUBLIC_URL)])
    text = (
        "🏮 *TRẠM ĐIỀU KHIỂN TEXT-ONLY*\n"
        f"🦙 Ollama: `{'🟢 hoạt động' if models else '⚫ mất kết nối'}`\n"
        f"🤖 Model đang dùng: `{await get_user_model(uid)}`\n"
        f"🎭 Persona: {persona['label']}\n"
        f"👤 Nickname: `{settings['nickname'] or '(chưa đặt)'}`\n"
        f"🌐 Tự động tìm web: `{'bật' if settings['auto_web'] else 'tắt'}`\n\n"
        "Bản này chỉ hỗ trợ chat văn bản, web search và ba skill: weather, news, crypto."
    )
    return text, InlineKeyboardMarkup(rows)


async def cmd_ui(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if is_allowed(update.effective_user.id):
        text, markup = await _render_main(update.effective_user.id)
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=markup)


async def handle_callback_query(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = update.effective_user.id
    if not is_allowed(uid):
        return
    data = query.data

    if data == "menu_main":
        text, markup = await _render_main(uid)
    elif data == "toggle_autoweb":
        settings = await db.get_settings(uid)
        await db.set_setting(uid, auto_web=not settings["auto_web"])
        text, markup = await _render_main(uid)
    elif data == "menu_model":
        models = await get_ollama_models()
        rows = [[InlineKeyboardButton(model, callback_data=f"set_model:{model}")] for model in models[:12]]
        rows.append([_back()])
        text, markup = "🦙 *Chọn mô hình Ollama*", InlineKeyboardMarkup(rows)
    elif data.startswith("set_model:"):
        await db.set_setting(uid, model=data.split(":", 1)[1])
        text, markup = await _render_main(uid)
    elif data == "menu_persona":
        rows = [
            [InlineKeyboardButton(value["label"], callback_data=f"set_persona:{key}")]
            for key, value in reasoning.PERSONAS.items()
        ]
        rows.append([_back()])
        text, markup = "🎭 *Chọn persona*", InlineKeyboardMarkup(rows)
    elif data.startswith("set_persona:"):
        await db.set_setting(uid, persona=data.split(":", 1)[1])
        text, markup = await _render_main(uid)
    elif data == "menu_help":
        text = "Gửi tin nhắn văn bản để chat. Dùng `/help` để xem toàn bộ lệnh."
        markup = InlineKeyboardMarkup([[_back()]])
    else:
        return

    try:
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=markup)
    except BadRequest as exc:
        if "not modified" not in str(exc).lower():
            raise
