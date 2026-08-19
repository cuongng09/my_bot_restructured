"""
handlers/commands.py — Tất cả các lệnh /command của bot.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import database as db
import local_voice
import reasoning
from skills.voice import groq_client
from skills.dashboard import skill_ping
from utils import (
    is_allowed, is_admin, is_addressed_in_group, is_rate_limited,
    notify_rate_limited, safe_reply, ACTIVE_GEN_TASKS,
    get_auto_web_mode, get_user_model, get_user_nickname,
)


# ── /start ────────────────────────────────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if is_allowed(update.effective_user.id):
        await safe_reply(
            update,
            "👋 Hệ thống đã sẵn sàng. Gõ `/ui` để mở bảng điều khiển, hoặc `/help` để xem hướng dẫn đầy đủ.\n\n"
            "📎 Gửi ảnh/PDF chứa chữ (Anh hoặc Việt) — mình tự nhận diện ngôn ngữ rồi OCR + dịch sang chiều còn lại.\n"
            "🎙️ Gửi voice — mình nghe và trả lời bằng cả chữ lẫn giọng nói.",
        )


# ── /help ─────────────────────────────────────────────────────────────────────
async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return
    text = (
        "📖 *HƯỚNG DẪN SỬ DỤNG*\n\n"
        "💬 *Trò chuyện:* gõ bất kỳ điều gì — mình trả lời tự nhiên, giữ ngữ cảnh hội thoại.\n"
        "🎙️ *Voice:* gửi tin nhắn thoại — mình nghe, trả lời bằng cả text lẫn giọng nói.\n"
        "`/stt <local|groq>` — chọn engine nghe giọng nói\n"
        "`/ttsmode <off|smart|always>` — bật/tắt trả lời kèm voice note\n"
        "🖼️ *Ảnh/PDF:* gửi ảnh hoặc PDF chứa chữ Anh/Việt — mình OCR + dịch sang chiều còn lại.\n\n"
        "*Lệnh nhanh:*\n"
        "`/ui` — mở bảng điều khiển trung tâm\n"
        "`/weather <thành phố>` — thời tiết + chất lượng không khí\n"
        "`/news [nguồn]` — tin tức nhanh (vnexpress, tuoitre, thanhnien, dantri, bbcvietnamese)\n"
        "`/autoweb` — bật/tắt tự động tra cứu web cho mọi tin nhắn\n"
        "`/nickname <tên>` — đặt tên gọi riêng\n"
        "`/persona <tên>` — đổi tính cách bot (ban_than / chuyen_gia / hai_huoc / co_van)\n"
        "`/voice <tên>` — đổi giọng đọc khi trả lời bằng voice\n"
        "`/export` — xuất lịch sử hội thoại ra file .txt\n"
        "`/stop` — dừng phản hồi AI đang tạo dở\n"
        "`/reset` — xóa lịch sử hội thoại\n"
        "`/ping` — kiểm tra kết nối tới Ollama\n"
        + ("`/shutdown`, `/reboot` — [Admin] quản trị server\n"
           if is_admin(update.effective_user.id) else "")
    )
    await safe_reply(update, text)


# ── /reset ────────────────────────────────────────────────────────────────────
async def cmd_reset(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if is_allowed(update.effective_user.id):
        await db.clear_history(update.effective_user.id)
        await update.message.reply_text("♻ Đã xóa sạch lịch sử hội thoại.")


# ── /stop ─────────────────────────────────────────────────────────────────────
async def cmd_stop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_allowed(uid):
        return
    task = ACTIVE_GEN_TASKS.get(uid)
    if task and not task.done():
        task.cancel()
        await safe_reply(update, "🚫 Đã gửi yêu cầu dừng — chờ vài giây để hoàn tất.")
    else:
        await safe_reply(update, "ℹ️ Hiện không có phản hồi nào đang tạo để dừng.")


# ── /export ───────────────────────────────────────────────────────────────────
async def cmd_export(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_allowed(uid):
        return
    history = await db.get_history(uid)
    if not history:
        return await safe_reply(update, "📭 Chưa có lịch sử hội thoại nào để xuất.")
    lines = [f"[{'Bạn' if m['role'] == 'user' else 'Bot'}] {m['content']}\n" for m in history]
    path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as tmp:
            tmp.write("\n".join(lines))
            path = tmp.name
        with open(path, "rb") as f:
            await update.message.reply_document(
                document=f, filename=f"chat_history_{uid}.txt",
                caption="🗂️ Lịch sử hội thoại của bạn.",
            )
    except Exception as e:
        await safe_reply(update, f"❌ Lỗi khi xuất lịch sử: {e}")
    finally:
        if path:
            Path(path).unlink(missing_ok=True)


# ── /nickname ─────────────────────────────────────────────────────────────────
async def cmd_nickname(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_allowed(uid):
        return
    if not ctx.args:
        cur = await get_user_nickname(uid)
        msg = (f"👤 Tên gọi hiện tại: *{cur}*" if cur
               else "👤 Bạn chưa đặt tên gọi riêng.\nDùng: `/nickname <tên>` — ví dụ `/nickname Minh`.")
        return await safe_reply(update, msg)
    name = " ".join(ctx.args).strip()[:50]
    await db.set_setting(uid, nickname=name)
    await safe_reply(update, f"✅ Từ giờ mình sẽ gọi bạn là *{name}* nhé!")


# ── /persona ──────────────────────────────────────────────────────────────────
async def cmd_persona(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_allowed(uid):
        return
    if not ctx.args:
        cur = (await db.get_settings(uid))["persona"]
        options = "\n".join(
            f"{'👉 ' if k == cur else '• '}`{k}` — {v['label']}"
            for k, v in reasoning.PERSONAS.items()
        )
        return await safe_reply(update, f"🎭 Dùng: `/persona <tên>`\n\nCác lựa chọn:\n{options}")
    key = ctx.args[0].strip().lower()
    if key not in reasoning.PERSONAS:
        return await safe_reply(update, "⚠️ Không tìm thấy persona này. Gõ `/persona` để xem danh sách.")
    await db.set_setting(uid, persona=key)
    await safe_reply(update, f"✅ Đã đổi sang tính cách: {reasoning.PERSONAS[key]['label']}")


# ── /voice ────────────────────────────────────────────────────────────────────
async def cmd_voice(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_allowed(uid):
        return
    voices = local_voice.list_available_voices()
    if not voices:
        return await safe_reply(update, "⚠️ Chưa cấu hình giọng Piper nào (xem PIPER_VOICE_PATHS trong .env).")
    if not ctx.args:
        cur = (await db.get_settings(uid))["tts_voice"] or "(mặc định)"
        return await safe_reply(
            update,
            f"🗣️ Dùng: `/voice <tên>`\n\nGiọng hiện tại: *{cur}*\nCác giọng có sẵn: {', '.join(voices)}",
        )
    name = ctx.args[0].strip()
    if name not in voices:
        return await safe_reply(update, f"⚠️ Không có giọng '{name}'. Có sẵn: {', '.join(voices)}")
    await db.set_setting(uid, tts_voice=name)
    await safe_reply(update, f"✅ Đã đổi giọng đọc sang '{name}'.")


# ── /stt ──────────────────────────────────────────────────────────────────────
async def cmd_stt(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_allowed(uid):
        return
    if not ctx.args:
        cur = (await db.get_settings(uid))["stt_engine"] or "local"
        groq_status = "✅ đã cấu hình" if groq_client else "❌ chưa cấu hình GROQ_API_KEY"
        return await safe_reply(
            update,
            f"🎙️ Dùng: `/stt <local|groq>`\n\nEngine hiện tại: *{cur}*\n\n"
            f"• `local` — faster-whisper, chạy offline hoàn toàn\n"
            f"• `groq` — Groq Whisper API, cần internet + GROQ_API_KEY ({groq_status})\n\n"
            f"ℹ️ Nếu engine chính lỗi, bot tự động thử engine còn lại.",
        )
    choice = ctx.args[0].strip().lower()
    if choice not in ("local", "groq"):
        return await safe_reply(update, "⚠️ Chỉ chọn `local` hoặc `groq`.")
    if choice == "groq" and not groq_client:
        return await safe_reply(update, "⚠️ Chưa cấu hình GROQ_API_KEY — không thể chọn engine groq.")
    await db.set_setting(uid, stt_engine=choice)
    await safe_reply(update, f"✅ Đã đổi engine nghe giọng nói sang: *{choice}*.")


# ── /ttsmode ──────────────────────────────────────────────────────────────────
async def cmd_ttsmode(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_allowed(uid):
        return
    if not ctx.args:
        cur = (await db.get_settings(uid))["voice_mode"] or "smart"
        return await safe_reply(
            update,
            f"🔊 Dùng: `/ttsmode <off|smart|always>`\n\nChế độ hiện tại: *{cur}*\n\n"
            f"• `off` — chỉ trả lời bằng text\n"
            f"• `smart` — tự đọc giọng nói cho câu trả lời không quá dài\n"
            f"• `always` — luôn đọc giọng nói, kể cả câu dài",
        )
    choice = ctx.args[0].strip().lower()
    if choice not in ("off", "smart", "always"):
        return await safe_reply(update, "⚠️ Chỉ chọn `off`, `smart` hoặc `always`.")
    await db.set_setting(uid, voice_mode=choice)
    await safe_reply(update, f"✅ Đã đổi chế độ voice reply sang: *{choice}*.")


# ── /ping ─────────────────────────────────────────────────────────────────────
async def cmd_ping(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return
    await safe_reply(update, await skill_ping())


# ── /weather ──────────────────────────────────────────────────────────────────
async def cmd_weather(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_allowed(uid) or not is_addressed_in_group(update):
        return
    if await is_rate_limited(uid):
        return await notify_rate_limited(update)
    from telegram.constants import ChatAction
    city = " ".join(ctx.args).strip() if ctx.args else ""
    if not city:
        return await safe_reply(update, "💡 Cách dùng: `/weather <thành phố>` — ví dụ `/weather Hà Nội`.")
    await update.effective_chat.send_action(ChatAction.TYPING)
    from skills.weather import skill_weather
    await safe_reply(update, await skill_weather(city))


# ── /news ─────────────────────────────────────────────────────────────────────
async def cmd_news(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_allowed(uid) or not is_addressed_in_group(update):
        return
    if await is_rate_limited(uid):
        return await notify_rate_limited(update)
    src = ctx.args[0].strip().lower() if ctx.args else "vnexpress"
    from telegram.constants import ChatAction
    await update.effective_chat.send_action(ChatAction.TYPING)
    from skills.news import skill_news
    await safe_reply(update, await skill_news(src))


# ── /autoweb ──────────────────────────────────────────────────────────────────
async def cmd_autoweb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_allowed(uid):
        return
    new_state = not await get_auto_web_mode(uid)
    await db.set_setting(uid, auto_web=new_state)
    msg = (
        "✅ Đã **BẬT** chế độ **Tự động tìm kiếm 🌐** — mọi tin nhắn đều tự tìm DuckDuckGo."
        if new_state else
        "⛔ Đã **TẮT** chế độ Tự động tìm kiếm."
    )
    await safe_reply(update, msg)


# ── /shutdown /reboot (Admin only) ────────────────────────────────────────────
def _sysaction_confirm_kb(action: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Xác nhận", callback_data=f"confirm_{action}"),
        InlineKeyboardButton("❌ Hủy",      callback_data="cancel_sysaction"),
    ]])


async def cmd_shutdown(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid):
        await update.message.reply_text("⛔ Bạn không có quyền dùng lệnh này.")
        return
    import os
    cmd_str = "shutdown /s /t 0" if os.name == 'nt' else "sudo shutdown -h now"
    await update.message.reply_text(
        f"⚠️ **XÁC NHẬN TẮT SERVER**\nServer sẽ TẮT NGUỒN hoàn toàn (`{cmd_str}`). Chắc chắn chứ?",
        parse_mode="Markdown", reply_markup=_sysaction_confirm_kb("shutdown"),
    )


async def cmd_reboot(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid):
        await update.message.reply_text("⛔ Bạn không có quyền dùng lệnh này.")
        return
    import os
    cmd_str = "shutdown /r /t 0" if os.name == 'nt' else "sudo reboot"
    await update.message.reply_text(
        f"⚠️ **XÁC NHẬN KHỞI ĐỘNG LẠI SERVER**\nServer sẽ REBOOT (`{cmd_str}`). Chắc chắn chứ?",
        parse_mode="Markdown", reply_markup=_sysaction_confirm_kb("reboot"),
    )
