"""
handlers/dashboard_handler.py — 🏮 TRẠM ĐIỀU KHIỂN: dashboard nút bấm (inline keyboard) + CallbackQueryHandler.

Kiến trúc menu (đi kèm breadcrumb "⬅️ Quay lại <cha>" nhất quán ở mọi màn hình con):

  🏮 Trạm chính  (trạng thái Ollama + model/persona/tên gọi hiện tại)
  │   └─ 🌐 Mở Trạm Điều Khiển Web  (admin, chỉ hiện nếu đã cấu hình WEBAPP_PUBLIC_URL)
  ├─ 💬 Trò chuyện       → Mô hình / Tính cách / Tên gọi / Giọng nói
  │   ├─ 🦙 Mô hình        (chọn model Ollama)
  │   ├─ 🎭 Tính cách      (chọn persona)
  │   └─ 🎙️ Giọng nói      → STT / Chế độ voice reply / Giọng đọc
  ├─ 🧰 Tiện ích         → Thời tiết / Tin tức / Dịch văn bản / Tự động tìm web
  ├─ 🖥️ Hệ thống (Admin) → CPU/RAM / Tệp tin / Ping / Trang web quản trị / Tắt-Khởi động lại
  └─ ❓ Trợ giúp

Mỗi nút chỉ làm đúng MỘT việc, tên nút luôn là hành động ở dạng chủ động, và trạng thái
hiện tại luôn hiển thị ngay tại chỗ (✅) thay vì phải đoán hoặc gõ lệnh để kiểm tra.
"""

from __future__ import annotations

from urllib.parse import urlparse

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import ContextTypes

import database as db
import local_voice
import reasoning
from bot_logger import logger
from config import WEBAPP_PUBLIC_URL
from llm_engine import get_ollama_models
from skills.dashboard import skill_ping, skill_sysadmin, run_sysaction
from skills.voice import groq_client
from skills.weather import skill_weather
from skills.news import skill_news
from utils import is_allowed, is_admin, safe_reply, get_auto_web_mode, get_user_model


async def _safe_edit_message_text(query, *args, **kwargs):
    """Wrapper an toàn quanh query.edit_message_text().

    Telegram trả lỗi `BadRequest: Message is not modified` khi nội dung + reply_markup
    mới gửi lên giống HỆT nội dung đang hiển thị (vd người dùng bấm lại nút vừa bấm,
    hoặc 2 lần bấm rất nhanh vào cùng 1 nút toggle trước khi tin nhắn kịp cập nhật).
    Đây không phải lỗi thật — tin nhắn đã đúng nội dung mong muốn rồi — nên chỉ cần bỏ
    qua thay vì để exception văng lên global_error_handler và làm callback bị coi là lỗi.
    Mọi lỗi BadRequest khác (network, entity quá dài, markup sai...) vẫn được raise lại
    bình thường để không che giấu lỗi thật.
    """
    try:
        return await query.edit_message_text(*args, **kwargs)
    except BadRequest as e:
        if "message is not modified" in str(e).lower():
            return None
        raise


# ─────────────────────────────────────────────────────────────────────────────
# 🔗 Validate WEBAPP_PUBLIC_URL trước khi dùng làm nút bấm Telegram
# ─────────────────────────────────────────────────────────────────────────────
_INVALID_BUTTON_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}
_webapp_url_warned = False  # chỉ log cảnh báo 1 lần, tránh spam log mỗi lần mở /ui


def _valid_webapp_button_url() -> str | None:
    """Trả về WEBAPP_PUBLIC_URL nếu dùng được làm nút inline Telegram, ngược lại None.

    Telegram Bot API từ chối TOÀN BỘ bàn phím inline (lỗi Button_url_invalid) nếu một
    nút có url trỏ tới localhost/127.0.0.1/0.0.0.0 hoặc thiếu scheme http(s) — vì máy
    người dùng mở Telegram không thể resolve các host đó về máy chạy bot. Nếu không
    validate trước, cả lệnh /ui sẽ crash (không hiện gì) thay vì chỉ riêng nút này lỗi.
    """
    global _webapp_url_warned
    url = (WEBAPP_PUBLIC_URL or "").strip()
    if not url:
        return None

    try:
        parsed = urlparse(url)
    except Exception:
        parsed = None

    host = (parsed.hostname or "").lower() if parsed else ""
    is_valid = bool(parsed) and parsed.scheme in ("http", "https") and host not in _INVALID_BUTTON_HOSTS

    if not is_valid and not _webapp_url_warned:
        _webapp_url_warned = True
        logger.warning(
            f"⚠️ WEBAPP_PUBLIC_URL='{url}' không dùng được làm nút Telegram (localhost/127.0.0.1 "
            f"hoặc thiếu http/https) — Telegram sẽ từ chối, nên nút '🌐 Mở Trạm Điều Khiển Web' "
            f"đã được TỰ ẨN để /ui không bị lỗi. Hãy đổi WEBAPP_PUBLIC_URL trong .env sang địa chỉ "
            f"IP LAN của máy chạy bot (vd http://192.168.1.10:8080) hoặc domain/HTTPS công khai."
        )
    return url if is_valid else None


# ─────────────────────────────────────────────────────────────────────────────
# 🏮 Trạm chính (main menu) — có trạng thái sống nên render bằng hàm async
# ─────────────────────────────────────────────────────────────────────────────
async def _render_main(uid: int) -> tuple[str, InlineKeyboardMarkup]:
    settings = await db.get_settings(uid)
    models = await get_ollama_models()
    seal = "🔴 HOẠT ĐỘNG" if models else "⚫ MẤT KẾT NỐI OLLAMA"

    persona_label = reasoning.PERSONAS.get(
        settings["persona"], reasoning.PERSONAS[reasoning.DEFAULT_PERSONA]
    )["label"]
    nickname_line = f"👤 Tên gọi: *{settings['nickname']}*" if settings["nickname"] else "👤 Tên gọi: _chưa đặt_"

    text = (
        f"🏮 *TRẠM ĐIỀU KHIỂN*\n"
        f"{seal}\n"
        f"┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈\n"
        f"🦙 Mô hình: `{settings['model'] or '(mặc định)'}`\n"
        f"🎭 Tính cách: {persona_label}\n"
        f"{nickname_line}"
    )
    rows = [
        [InlineKeyboardButton("💬 Trò chuyện", callback_data="menu_chat"),
         InlineKeyboardButton("🧰 Tiện ích",   callback_data="menu_skills")],
    ]
    if is_admin(uid):
        rows.append([
            InlineKeyboardButton("🖥️ Hệ thống", callback_data="menu_sys"),
            InlineKeyboardButton("❓ Trợ giúp",  callback_data="menu_help"),
        ])
        if webapp_url := _valid_webapp_button_url():
            rows.append([InlineKeyboardButton("🌐 Mở Trạm Điều Khiển Web", url=webapp_url)])
    else:
        rows.append([InlineKeyboardButton("❓ Trợ giúp", callback_data="menu_help")])
    return text, InlineKeyboardMarkup(rows)


def _back(to: str = "menu_main", label: str = "Trạm chính") -> InlineKeyboardButton:
    return InlineKeyboardButton(f"⬅️ Quay lại {label}", callback_data=to)


async def cmd_ui(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_allowed(uid):
        text, markup = await _render_main(uid)
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=markup)


# ─────────────────────────────────────────────────────────────────────────────
# Callback dispatcher
# ─────────────────────────────────────────────────────────────────────────────
async def handle_callback_query(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data, uid = query.data, update.effective_user.id

    if not is_allowed(uid):
        return

    # ── Trạm chính ────────────────────────────────────────────────────────────
    if data == "menu_main":
        text, markup = await _render_main(uid)
        await _safe_edit_message_text(query, text, parse_mode="Markdown", reply_markup=markup)

    elif data == "menu_help":
        from handlers.commands import cmd_help
        await cmd_help(update, ctx)

    # ── 💬 Trò chuyện ─────────────────────────────────────────────────────────
    elif data == "menu_chat":
        settings = await db.get_settings(uid)
        kb = [
            [InlineKeyboardButton("🦙 Đổi mô hình",   callback_data="menu_models"),
             InlineKeyboardButton("🎭 Đổi tính cách", callback_data="menu_persona")],
            [InlineKeyboardButton("👤 Đặt tên gọi riêng", callback_data="ui_set_nickname"),
             InlineKeyboardButton("🎙️ Cài đặt giọng nói", callback_data="menu_voice")],
            [_back()],
        ]
        await _safe_edit_message_text(query, 
            f"💬 *TRÒ CHUYỆN*\n"
            f"Mô hình: `{settings['model'] or '(mặc định)'}` • "
            f"Tính cách: {reasoning.PERSONAS.get(settings['persona'], {}).get('label', '—')}",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb),
        )

    elif data == "ui_set_nickname":
        await safe_reply(
            update,
            "👤 Gõ lệnh `/nickname <tên>` để đặt tên gọi riêng — ví dụ `/nickname Minh`.\n"
            "_(Tên gọi là văn bản tự do nên cần gõ lệnh thay vì chọn nút.)_",
        )

    # ── 🎭 Tính cách (persona) ────────────────────────────────────────────────
    elif data == "menu_persona":
        current = (await db.get_settings(uid))["persona"]
        kb = [
            [InlineKeyboardButton(
                f"{'✅ ' if key == current else ''}{p['label']}", callback_data=f"set_persona_{key}"
            )] for key, p in reasoning.PERSONAS.items()
        ]
        kb.append([_back("menu_chat", "Trò chuyện")])
        await _safe_edit_message_text(query, 
            "🎭 *CHỌN TÍNH CÁCH*\n_Ảnh hưởng đến văn phong bot trả lời — đổi được bất cứ lúc nào._",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb),
        )

    elif data.startswith("set_persona_"):
        key = data.replace("set_persona_", "")
        if key not in reasoning.PERSONAS:
            await query.answer("⚠️ Không tìm thấy tính cách này.", show_alert=True)
            return
        await db.set_setting(uid, persona=key)
        await query.answer(f"Đã đổi sang {reasoning.PERSONAS[key]['label']}")
        kb = [
            [InlineKeyboardButton(
                f"{'✅ ' if k == key else ''}{p['label']}", callback_data=f"set_persona_{k}"
            )] for k, p in reasoning.PERSONAS.items()
        ]
        kb.append([_back("menu_chat", "Trò chuyện")])
        await _safe_edit_message_text(query, 
            f"🎭 *CHỌN TÍNH CÁCH*\n✅ Đang dùng: {reasoning.PERSONAS[key]['label']}",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb),
        )

    # ── 🎙️ Giọng nói (STT/TTS) ────────────────────────────────────────────────
    elif data == "menu_voice":
        settings = await db.get_settings(uid)
        groq_note = "✅" if groq_client else "❌ chưa cấu hình"
        kb = [
            [InlineKeyboardButton(
                f"🎧 Nghe giọng nói: {settings['stt_engine'] or 'local'}", callback_data="menu_stt"
            )],
            [InlineKeyboardButton(
                f"🔊 Trả lời bằng voice: {settings['voice_mode'] or 'smart'}", callback_data="menu_ttsmode"
            )],
            [InlineKeyboardButton(
                f"🗣️ Giọng đọc: {settings['tts_voice'] or '(mặc định)'}", callback_data="menu_voice_pick"
            )],
            [_back("menu_chat", "Trò chuyện")],
        ]
        await _safe_edit_message_text(query, 
            f"🎙️ *CÀI ĐẶT GIỌNG NÓI*\nGroq Whisper (engine dự phòng): {groq_note}",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb),
        )

    elif data == "menu_stt":
        current = (await db.get_settings(uid))["stt_engine"] or "local"
        options = [("local", "🖥️ Local (Voicebox Docker)")]
        if groq_client:
            options.append(("groq", "☁️ Groq Whisper API (cần internet)"))
        kb = [[InlineKeyboardButton(
            f"{'✅ ' if key == current else ''}{label}", callback_data=f"set_stt_{key}"
        )] for key, label in options]
        kb.append([_back("menu_voice", "Giọng nói")])
        await _safe_edit_message_text(query, 
            "🎧 *ENGINE NGHE GIỌNG NÓI*\n_Nếu engine chính lỗi, bot tự chuyển sang engine còn lại._",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb),
        )

    elif data.startswith("set_stt_"):
        choice = data.replace("set_stt_", "")
        await db.set_setting(uid, stt_engine=choice)
        await query.answer(f"Đã đổi engine nghe giọng nói: {choice}")
        options = [("local", "🖥️ Local (Voicebox Docker)")]
        if groq_client:
            options.append(("groq", "☁️ Groq Whisper API (cần internet)"))
        kb = [[InlineKeyboardButton(
            f"{'✅ ' if key == choice else ''}{label}", callback_data=f"set_stt_{key}"
        )] for key, label in options]
        kb.append([_back("menu_voice", "Giọng nói")])
        await _safe_edit_message_text(query, 
            f"🎧 *ENGINE NGHE GIỌNG NÓI*\n✅ Đang dùng: {choice}",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb),
        )

    elif data == "menu_ttsmode":
        current = (await db.get_settings(uid))["voice_mode"] or "smart"
        options = [
            ("off",    "🔇 Tắt — chỉ trả lời bằng chữ"),
            ("smart",  "🙂 Thông minh — tự đọc câu trả lời ngắn"),
            ("always", "🔊 Luôn đọc — kể cả câu trả lời dài"),
        ]
        kb = [[InlineKeyboardButton(
            f"{'✅ ' if key == current else ''}{label}", callback_data=f"set_tts_{key}"
        )] for key, label in options]
        kb.append([_back("menu_voice", "Giọng nói")])
        await _safe_edit_message_text(query, 
            "🔊 *CHẾ ĐỘ TRẢ LỜI BẰNG VOICE*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb),
        )

    elif data.startswith("set_tts_"):
        choice = data.replace("set_tts_", "")
        await db.set_setting(uid, voice_mode=choice)
        await query.answer(f"Đã đổi chế độ voice reply: {choice}")
        options = [
            ("off",    "🔇 Tắt — chỉ trả lời bằng chữ"),
            ("smart",  "🙂 Thông minh — tự đọc câu trả lời ngắn"),
            ("always", "🔊 Luôn đọc — kể cả câu trả lời dài"),
        ]
        kb = [[InlineKeyboardButton(
            f"{'✅ ' if key == choice else ''}{label}", callback_data=f"set_tts_{key}"
        )] for key, label in options]
        kb.append([_back("menu_voice", "Giọng nói")])
        await _safe_edit_message_text(query, 
            f"🔊 *CHẾ ĐỘ TRẢ LỜI BẰNG VOICE*\n✅ Đang dùng: {choice}",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb),
        )

    elif data == "menu_voice_pick":
        voices = local_voice.list_available_voices()
        if not voices:
            await _safe_edit_message_text(query, 
                "🗣️ *GIỌNG ĐỌC*\n⚠️ Chưa cấu hình giọng Piper nào (xem `PIPER_VOICE_PATHS` trong `.env`).",
                parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[_back("menu_voice", "Giọng nói")]]),
            )
            return
        current = (await db.get_settings(uid))["tts_voice"]
        kb = [[InlineKeyboardButton(
            f"{'✅ ' if v == current else ''}{v}", callback_data=f"set_voice_{v}"
        )] for v in voices]
        kb.append([_back("menu_voice", "Giọng nói")])
        await _safe_edit_message_text(query, 
            "🗣️ *CHỌN GIỌNG ĐỌC*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb),
        )

    elif data.startswith("set_voice_"):
        name = data.replace("set_voice_", "")
        voices = local_voice.list_available_voices()
        if name not in voices:
            await query.answer("⚠️ Không tìm thấy giọng này.", show_alert=True)
            return
        await db.set_setting(uid, tts_voice=name)
        await query.answer(f"Đã đổi giọng đọc: {name}")
        kb = [[InlineKeyboardButton(
            f"{'✅ ' if v == name else ''}{v}", callback_data=f"set_voice_{v}"
        )] for v in voices]
        kb.append([_back("menu_voice", "Giọng nói")])
        await _safe_edit_message_text(query, 
            f"🗣️ *CHỌN GIỌNG ĐỌC*\n✅ Đang dùng: {name}",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb),
        )

    # ── 🦙 Mô hình (models) ───────────────────────────────────────────────────
    elif data == "menu_models":
        models = await get_ollama_models()
        current_model = await get_user_model(uid)
        if not models:
            await _safe_edit_message_text(query, 
                "🦙 *MÔ HÌNH (OLLAMA)*\n⚫ Không kết nối được Ollama — kiểm tra `ollama serve` đã chạy chưa.",
                parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[_back("menu_chat", "Trò chuyện")]]),
            )
            return
        kb = [[InlineKeyboardButton(
            f"{'✅ ' if m == current_model else ''}{m}", callback_data=f"set_model_{m}"
        )] for m in models]
        kb.append([_back("menu_chat", "Trò chuyện")])
        await _safe_edit_message_text(query, 
            "🦙 *CHỌN MÔ HÌNH (OLLAMA)*\n_Đổi mô hình sẽ reset lịch sử hội thoại hiện tại._",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb),
        )

    elif data.startswith("set_model_"):
        new_model = data.replace("set_model_", "")
        await db.set_setting(uid, model=new_model)
        await db.clear_history(uid)
        text, markup = await _render_main(uid)
        await _safe_edit_message_text(query, 
            f"✅ Đã đổi sang mô hình `{new_model}`. Lịch sử hội thoại đã được làm mới.\n\n{text}",
            parse_mode="Markdown", reply_markup=markup,
        )

    # ── 🧰 Tiện ích ───────────────────────────────────────────────────────────
    elif data == "menu_skills":
        auto_web = await get_auto_web_mode(uid)
        auto_web_label = "🌐 Tự động tìm web: BẬT ✅" if auto_web else "🌐 Tự động tìm web: TẮT ⛔"
        kb = [
            [InlineKeyboardButton("🌤️ Hà Nội",        callback_data="ui_wf_hanoi"),
             InlineKeyboardButton("🌤️ Hồ Chí Minh",   callback_data="ui_wf_hcm"),
             InlineKeyboardButton("🌤️ Đà Nẵng",       callback_data="ui_wf_danang")],
            [InlineKeyboardButton("📰 VnExpress",      callback_data="ui_nw_vnexpress"),
             InlineKeyboardButton("📰 Tuổi Trẻ",       callback_data="ui_nw_tuoitre")],
            [InlineKeyboardButton("📰 Thanh Niên",     callback_data="ui_nw_thanhnien"),
             InlineKeyboardButton("📰 Dân Trí",        callback_data="ui_nw_dantri")],
            [InlineKeyboardButton("📰 BBC Tiếng Việt", callback_data="ui_nw_bbcvietnamese")],
            [InlineKeyboardButton("🔤 Dịch văn bản",   callback_data="ui_translation_menu")],
            [InlineKeyboardButton(auto_web_label,      callback_data="ui_toggle_auto_web")],
            [_back()],
        ]
        await _safe_edit_message_text(query, 
            "🧰 *TIỆN ÍCH*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb),
        )

    elif data == "ui_toggle_auto_web":
        new_state = not await get_auto_web_mode(uid)
        await db.set_setting(uid, auto_web=new_state)
        msg = (
            "✅ Đã *bật* Tự động tìm web thông minh — bot sẽ tự phân tích câu hỏi để tra cứu khi cần với từ khóa tối ưu."
            if new_state else
            "⛔ Đã *tắt* Tự động tìm web — bot chỉ tìm web khi có từ khóa gợi ý."
        )
        await query.answer("Đã đổi chế độ tự động tìm web")
        await safe_reply(update, msg)

    elif data == "ui_translation_menu":
        kb = [
            [InlineKeyboardButton("🇬🇧 Anh ➡️ 🇻🇳 Việt", callback_data="text_trans_en_vi"),
             InlineKeyboardButton("🇻🇳 Việt ➡️ 🇬🇧 Anh",  callback_data="text_trans_vi_en")],
            [_back("menu_skills", "Tiện ích")],
        ]
        await _safe_edit_message_text(query, 
            "🔤 *DỊCH VĂN BẢN (GOOGLE)*\n_Chọn hướng dịch rồi gửi đoạn văn bản cần dịch:_\n\n"
            "💡 _Mẹo: gửi thẳng ẢNH hoặc PDF — mình tự OCR + dịch, không cần chọn hướng._",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb),
        )

    elif data.startswith("text_trans_"):
        await db.set_setting(uid, media_mode=data)
        direction = "Tiếng Anh ➡️ Tiếng Việt" if "en_vi" in data else "Tiếng Việt ➡️ Tiếng Anh"
        await safe_reply(update, f"✅ Đã bật *Dịch văn bản ({direction})*.\n\n⌨️ Nhập đoạn văn bản cần dịch!")

    # ── Rút gọn: thời tiết & tin tức ─────────────────────────────────────────
    elif data == "ui_wf_hanoi":
        await safe_reply(update, await skill_weather("Hà Nội"))
    elif data == "ui_wf_hcm":
        await safe_reply(update, await skill_weather("Hồ Chí Minh"))
    elif data == "ui_wf_danang":
        await safe_reply(update, await skill_weather("Đà Nẵng"))
    elif data.startswith("ui_nw_"):
        await safe_reply(update, await skill_news(data.replace("ui_nw_", "")))

    # ── 🖥️ Hệ thống (Admin) ───────────────────────────────────────────────────
    elif data == "menu_sys":
        if not is_admin(uid):
            await query.answer("⛔ Bạn không có quyền dùng chức năng này.", show_alert=True)
            return
        kb = [
            [InlineKeyboardButton("📊 CPU/RAM",     callback_data="sys_stats"),
             InlineKeyboardButton("📁 Xem tệp tin", callback_data="sys_files")],
            [InlineKeyboardButton("🏓 Ping Ollama", callback_data="sys_ping")],
        ]
        if webapp_url := _valid_webapp_button_url():
            kb.append([InlineKeyboardButton("🌐 Mở Trạm Điều Khiển Web", url=webapp_url)])
        kb.append([
            InlineKeyboardButton("🔁 Khởi động lại", callback_data="sys_reboot"),
            InlineKeyboardButton("🛑 Tắt server",    callback_data="sys_shutdown"),
        ])
        kb.append([_back()])
        await _safe_edit_message_text(query, 
            "🖥️ *HỆ THỐNG* _(Admin)_", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb),
        )

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

    elif data in ("sys_reboot", "sys_shutdown"):
        if not is_admin(uid):
            await query.answer("⛔ Bạn không có quyền.", show_alert=True)
            return
        action = "reboot" if data == "sys_reboot" else "shutdown"
        from handlers.commands import _sysaction_confirm_kb
        verb = "KHỞI ĐỘNG LẠI" if action == "reboot" else "TẮT NGUỒN hoàn toàn"
        await _safe_edit_message_text(query, 
            f"⚠️ *XÁC NHẬN*\nServer sẽ *{verb}*. Chắc chắn chứ?",
            parse_mode="Markdown", reply_markup=_sysaction_confirm_kb(action),
        )

    # ── Xác nhận tắt/khởi động lại ────────────────────────────────────────────
    elif data in ("confirm_shutdown", "confirm_reboot"):
        if not is_admin(uid):
            await _safe_edit_message_text(query, "⛔ Bạn không có quyền thực hiện thao tác này.")
            return
        action = "shutdown" if data == "confirm_shutdown" else "reboot"
        actor = update.effective_user
        logger.warning(
            f"🛑 SYSTEM ACTION '{action}' được xác nhận bởi uid={uid} "
            f"(@{actor.username if actor and actor.username else 'N/A'})"
        )
        await _safe_edit_message_text(query, 
            f"⏳ Đang thực thi lệnh {'tắt' if action == 'shutdown' else 'khởi động lại'} server..."
        )
        await safe_reply(update, await run_sysaction(action))

    elif data == "cancel_sysaction":
        await _safe_edit_message_text(query, "↩️ Đã hủy thao tác.")