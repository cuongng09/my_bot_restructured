"""
handlers/dashboard_handler.py — Dashboard inline keyboard UI + CallbackQueryHandler.
"""

from __future__ import annotations

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import database as db
from bot_logger import logger
from llm_engine import get_ollama_models
from skills.dashboard import skill_ping, skill_sysadmin, run_sysaction
from skills.weather import skill_weather
from skills.news import skill_news
from utils import is_allowed, is_admin, safe_reply, get_auto_web_mode, get_user_model


# ── Main menu ─────────────────────────────────────────────────────────────────
def get_main_menu(uid: int = 0) -> InlineKeyboardMarkup:
    rows = [[
        InlineKeyboardButton("🦙 Chọn LLM Model",       callback_data="menu_models"),
        InlineKeyboardButton("🔍 Trung Tâm Tiện Ích",   callback_data="menu_skills"),
    ]]
    if is_admin(uid):
        rows.append([
            InlineKeyboardButton("🖥️ Quản trị Server", callback_data="menu_sys"),
            InlineKeyboardButton("❓ Trợ giúp",         callback_data="menu_help"),
        ])
    else:
        rows.append([InlineKeyboardButton("❓ Trợ giúp", callback_data="menu_help")])
    return InlineKeyboardMarkup(rows)


async def cmd_ui(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_allowed(uid):
        await update.message.reply_text("🛠 **BẢNG ĐIỀU KHIỂN TRUNG TÂM**", reply_markup=get_main_menu(uid))


# ── Callback dispatcher ───────────────────────────────────────────────────────
async def handle_callback_query(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data, uid = query.data, update.effective_user.id

    if not is_allowed(uid):
        return

    # ── System actions (confirm / cancel) ────────────────────────────────────
    if data in ("confirm_shutdown", "confirm_reboot"):
        if not is_admin(uid):
            await query.edit_message_text("⛔ Bạn không có quyền thực hiện thao tác này.")
            return
        action = "shutdown" if data == "confirm_shutdown" else "reboot"
        actor = update.effective_user
        logger.warning(
            f"🛑 SYSTEM ACTION '{action}' được xác nhận bởi uid={uid} "
            f"(@{actor.username if actor and actor.username else 'N/A'})"
        )
        await query.edit_message_text(
            f"⏳ Đang thực thi lệnh {'tắt' if action == 'shutdown' else 'khởi động lại'} server..."
        )
        result = await run_sysaction(action)
        await safe_reply(update, result)
        return

    elif data == "cancel_sysaction":
        await query.edit_message_text("↩️ Đã hủy thao tác.")
        return

    # ── Menu navigation ───────────────────────────────────────────────────────
    elif data == "menu_main":
        await query.edit_message_text("🛠 **BẢNG ĐIỀU KHIỂN TRUNG TÂM**", reply_markup=get_main_menu(uid))

    elif data == "menu_help":
        from handlers.commands import cmd_help
        await cmd_help(update, ctx)

    elif data == "menu_skills":
        auto_web = await get_auto_web_mode(uid)
        label = "🌐 Tự động tìm kiếm: BẬT ✅" if auto_web else "🌐 Tự động tìm kiếm: TẮT ⛔"
        kb = [
            [InlineKeyboardButton("🌤️ Hà Nội",        callback_data="ui_wf_hanoi"),
             InlineKeyboardButton("🌤️ Hồ Chí Minh",   callback_data="ui_wf_hcm"),
             InlineKeyboardButton("🌤️ Đà Nẵng",       callback_data="ui_wf_danang")],
            [InlineKeyboardButton("📰 VnExpress",      callback_data="ui_nw_vnexpress"),
             InlineKeyboardButton("📰 Tuổi Trẻ",       callback_data="ui_nw_tuoitre")],
            [InlineKeyboardButton("📰 Thanh Niên",     callback_data="ui_nw_thanhnien"),
             InlineKeyboardButton("📰 Dân Trí",        callback_data="ui_nw_dantri")],
            [InlineKeyboardButton("📰 BBC Tiếng Việt", callback_data="ui_nw_bbcvietnamese")],
            [InlineKeyboardButton("🔤 Dịch Văn Bản",  callback_data="ui_translation_menu"),
             InlineKeyboardButton("👤 Tên gọi riêng",  callback_data="ui_set_nickname")],
            [InlineKeyboardButton(label,               callback_data="ui_toggle_auto_web")],
            [InlineKeyboardButton("⬅️ Trở lại",        callback_data="menu_main")],
        ]
        await query.edit_message_text(
            "🔍 **TRUNG TÂM TIỆN ÍCH & SKILLS HỆ THỐNG**\n_Lựa chọn chức năng:_",
            reply_markup=InlineKeyboardMarkup(kb),
        )

    elif data == "menu_sys":
        if not is_admin(uid):
            await query.answer("⛔ Bạn không có quyền dùng chức năng này.", show_alert=True)
            return
        kb = [
            [InlineKeyboardButton("📊 CPU/RAM",       callback_data="sys_stats"),
             InlineKeyboardButton("📁 Xem tệp tin",   callback_data="sys_files")],
            [InlineKeyboardButton("🏓 Ping Ollama",   callback_data="sys_ping")],
            [InlineKeyboardButton("🔁 Restart server",callback_data="sys_reboot"),
             InlineKeyboardButton("🛑 Tắt Server",    callback_data="sys_shutdown")],
            [InlineKeyboardButton("⬅️ Trở lại",       callback_data="menu_main")],
        ]
        await query.edit_message_text("🖥️ **System Admin Dashboard**", reply_markup=InlineKeyboardMarkup(kb))

    # ── Skills shortcuts ──────────────────────────────────────────────────────
    elif data == "ui_set_nickname":
        await safe_reply(update, "👤 Gõ lệnh `/nickname <tên>` để đặt tên gọi riêng.")

    elif data == "ui_toggle_auto_web":
        new_state = not await get_auto_web_mode(uid)
        await db.set_setting(uid, auto_web=new_state)
        msg = (
            "✅ Đã **BẬT** chế độ **Tự động tìm kiếm 🌐**\n\nMọi tin nhắn sẽ tự tra cứu dữ liệu web thời gian thực."
            if new_state else
            "⛔ Đã **TẮT** chế độ Tự động tìm kiếm. Bot quay lại chỉ tìm web khi có từ khóa gợi ý."
        )
        await query.answer("Đã đổi chế độ tự động tìm kiếm", show_alert=False)
        await safe_reply(update, msg)

    elif data == "ui_translation_menu":
        kb = [
            [InlineKeyboardButton("🇬🇧 Anh ➡️ 🇻🇳 Việt", callback_data="text_trans_en_vi"),
             InlineKeyboardButton("🇻🇳 Việt ➡️ 🇬🇧 Anh",  callback_data="text_trans_vi_en")],
            [InlineKeyboardButton("⬅️ Trở lại Trung Tâm Tiện Ích", callback_data="menu_skills")],
        ]
        await query.edit_message_text(
            "🔤 **DỊCH VĂN BẢN TRỰC TIẾP (GOOGLE):**\n_Chọn hướng dịch rồi gửi đoạn văn bản:_\n\n"
            "💡 _Mẹo: gửi thẳng ẢNH hoặc PDF để mình tự OCR + dịch._",
            reply_markup=InlineKeyboardMarkup(kb),
        )

    elif data.startswith("text_trans_"):
        await db.set_setting(uid, media_mode=data)
        direction = "Tiếng Anh ➡️ Tiếng Việt" if "en_vi" in data else "Tiếng Việt ➡️ Tiếng Anh"
        await safe_reply(
            update,
            f"✅ Đã kích hoạt: **Dịch văn bản ({direction})**.\n\n⌨️ Hãy nhập đoạn văn bản bạn muốn dịch!",
        )

    # ── Model selection ───────────────────────────────────────────────────────
    elif data == "menu_models":
        models = await get_ollama_models()
        current_model = await get_user_model(uid)
        if not models:
            await query.edit_message_text(
                "🦙 **Hệ thống Mô hình (Ollama)**\n\n❌ Không lấy được danh sách model.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Trở lại", callback_data="menu_main")]]),
            )
            return
        kb = [[InlineKeyboardButton(
            f"{'✅ ' if m == current_model else ''}{m}", callback_data=f"set_model_{m}"
        )] for m in models]
        kb.append([InlineKeyboardButton("⬅️ Trở lại", callback_data="menu_main")])
        await query.edit_message_text("🦙 **Hệ thống Mô hình (Ollama)**", reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith("set_model_"):
        new_model = data.replace("set_model_", "")
        await db.set_setting(uid, model=new_model)
        await db.clear_history(uid)
        await query.edit_message_text(
            f"✅ Đã đổi sang mô hình: `{new_model}`.\n♻️ Lịch sử hội thoại đã được reset.",
            reply_markup=get_main_menu(uid),
        )

    # ── Weather shortcuts ─────────────────────────────────────────────────────
    elif data == "ui_wf_hanoi":
        await safe_reply(update, await skill_weather("Hà Nội"))
    elif data == "ui_wf_hcm":
        await safe_reply(update, await skill_weather("Hồ Chí Minh"))
    elif data == "ui_wf_danang":
        await safe_reply(update, await skill_weather("Đà Nẵng"))

    elif data.startswith("ui_nw_"):
        src = data.replace("ui_nw_", "")
        await safe_reply(update, await skill_news(src))

    # ── Sysadmin shortcuts ────────────────────────────────────────────────────
    elif data in ("sys_stats", "sys_files", "sys_ping"):
        if not is_admin(uid):
            await query.answer("⛔ Bạn không có quyền dùng chức năng này.", show_alert=True)
            return
        if data == "sys_stats":
            await safe_reply(update, await skill_sysadmin("stats"))
        elif data == "sys_files":
            await safe_reply(update, await skill_sysadmin("files"))
        else:
            await safe_reply(update, await skill_ping())

    elif data == "sys_reboot":
        if not is_admin(uid):
            await query.answer("⛔ Bạn không có quyền.", show_alert=True)
            return
        from handlers.commands import _sysaction_confirm_kb
        await query.edit_message_text(
            "⚠️ **XÁC NHẬN KHỞI ĐỘNG LẠI SERVER**\nServer sẽ REBOOT. Chắc chắn chứ?",
            reply_markup=_sysaction_confirm_kb("reboot"),
        )
    elif data == "sys_shutdown":
        if not is_admin(uid):
            await query.answer("⛔ Bạn không có quyền.", show_alert=True)
            return
        from handlers.commands import _sysaction_confirm_kb
        await query.edit_message_text(
            "⚠️ **XÁC NHẬN TẮT SERVER**\nServer sẽ TẮT NGUỒN hoàn toàn. Chắc chắn chứ?",
            reply_markup=_sysaction_confirm_kb("shutdown"),
        )
