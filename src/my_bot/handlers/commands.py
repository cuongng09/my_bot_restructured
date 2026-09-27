"""Core text command handlers."""

from __future__ import annotations

import tempfile
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from my_bot.core import database as db
from my_bot.core.utils import (
    ACTIVE_GEN_TASKS, get_auto_web_mode, get_user_model, get_user_nickname,
    is_admin, is_allowed, safe_reply,
)
from my_bot.core.llm_engine import get_ollama_models
from my_bot.skills.news import skill_news
from my_bot.skills.weather import skill_weather

__all__ = [
    "cmd_start", "cmd_help", "cmd_reset", "cmd_resetmemory", "cmd_stop",
    "cmd_export", "cmd_nickname", "cmd_persona", "cmd_ping", "cmd_weather",
    "cmd_news", "cmd_autoweb", "cmd_shutdown", "cmd_reboot",
]


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if is_allowed(update.effective_user.id):
        await safe_reply(update, "👋 Bot text-only đã sẵn sàng. Gõ `/ui` để mở bảng điều khiển hoặc `/help` để xem hướng dẫn.")


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_allowed(uid):
        return
    admin = "`/ping`, `/shutdown`, `/reboot` — quản trị viên\n" if is_admin(uid) else ""
    await safe_reply(update, (
        "📖 *HƯỚNG DẪN TEXT-ONLY*\n\n"
        "Gửi tin nhắn văn bản để trò chuyện với Ollama; bot giữ ngữ cảnh, persona và nickname.\n"
        "`/ui` — mô hình, persona, tự động tìm web\n"
        "`/nickname <tên>` — đặt tên gọi\n"
        "`/persona <ban_than|chuyen_gia|hai_huoc|co_van>` — chọn phong cách\n"
        "`/autoweb [on|off]` — bật/tắt tìm kiếm web\n"
        "`/weather <thành phố>` — thời tiết\n"
        "`/news [nguồn]` — tin tức\n"
        "`/export` — xuất lịch sử `.txt`\n"
        "`/stop`, `/reset`, `/resetmemory` — điều khiển hội thoại\n"
        f"{admin}"
        "\nKhông hỗ trợ voice, ảnh, OCR, dịch ảnh hoặc file Word/Excel/PDF."
    ))


async def cmd_reset(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if is_allowed(update.effective_user.id):
        await db.clear_history(update.effective_user.id)
        await safe_reply(update, "♻ Đã xóa lịch sử hội thoại.")


async def cmd_resetmemory(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if is_allowed(update.effective_user.id):
        await db.clear_profile(update.effective_user.id)
        await safe_reply(update, "🧠 Đã xóa hồ sơ trí nhớ dài hạn.")


async def cmd_stop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_allowed(uid):
        return
    task = ACTIVE_GEN_TASKS.get(uid)
    if task and not task.done():
        task.cancel()
        await safe_reply(update, "🚫 Đã gửi yêu cầu dừng phản hồi.")
    else:
        await safe_reply(update, "ℹ️ Không có phản hồi đang tạo.")


async def cmd_export(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_allowed(uid):
        return
    history = await db.get_history(uid)
    if not history:
        return await safe_reply(update, "📭 Chưa có lịch sử để xuất.")
    path = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as file:
            path = Path(file.name)
            file.write("\n\n".join(
                f"[{'Bạn' if item['role'] == 'user' else 'Bot'}] {item['content']}"
                for item in history
            ))
        with path.open("rb") as file:
            await update.message.reply_document(file, filename=f"chat_history_{uid}.txt")
    finally:
        if path:
            path.unlink(missing_ok=True)


async def cmd_nickname(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_allowed(uid):
        return
    if not ctx.args:
        current = await get_user_nickname(uid)
        return await safe_reply(update, f"👤 Tên gọi hiện tại: {current or '(chưa đặt)'}")
    await db.set_setting(uid, nickname=" ".join(ctx.args).strip()[:80])
    await safe_reply(update, "✅ Đã lưu tên gọi.")


async def cmd_persona(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_allowed(uid):
        return
    allowed = {"ban_than", "chuyen_gia", "hai_huoc", "co_van"}
    choice = ctx.args[0].lower() if ctx.args else ""
    if choice not in allowed:
        return await safe_reply(update, "Dùng một trong: `ban_than`, `chuyen_gia`, `hai_huoc`, `co_van`.")
    await db.set_setting(uid, persona=choice)
    await safe_reply(update, f"✅ Persona hiện tại: `{choice}`")


async def cmd_ping(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if is_admin(update.effective_user.id):
        models = await get_ollama_models(force=True)
        await safe_reply(update, f"🏓 Ollama {'đang hoạt động' if models else 'không kết nối được'}." )


async def cmd_weather(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if is_allowed(update.effective_user.id):
        await safe_reply(update, await skill_weather(" ".join(ctx.args).strip() or "Hà Nội"))


async def cmd_news(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if is_allowed(update.effective_user.id):
        await safe_reply(update, await skill_news(ctx.args[0] if ctx.args else "vnexpress"))


async def cmd_autoweb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_allowed(uid):
        return
    current = await get_auto_web_mode(uid)
    value = ctx.args[0].lower() if ctx.args else ("off" if current else "on")
    if value not in {"on", "off"}:
        return await safe_reply(update, "Dùng `/autoweb on` hoặc `/autoweb off`.")
    await db.set_setting(uid, auto_web=value == "on")
    await safe_reply(update, f"🌐 Tìm web: {'bật' if value == 'on' else 'tắt'}")


async def cmd_shutdown(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if is_admin(update.effective_user.id):
        await safe_reply(update, "⚠️ Lệnh shutdown không được thực hiện qua chat trong bản text-only.")


async def cmd_reboot(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if is_admin(update.effective_user.id):
        await safe_reply(update, "⚠️ Lệnh reboot không được thực hiện qua chat trong bản text-only.")
