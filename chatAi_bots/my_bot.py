"""
my_bot.py — Trợ lý AI đa năng trên Telegram (chạy LLM cục bộ qua Ollama).
             ENTRYPOINT DUY NHẤT — chỉ khởi tạo & nối các module lại, không chứa logic nghiệp vụ.

Tính năng (xem chi tiết trong từng module ở skills/ và handlers/):
  💬 Chat AI streaming (Ollama, giữ ngữ cảnh hội thoại)          → llm_engine.py, handlers/text_handler.py
  🌐 Tự tra cứu web thời gian thực (RAG)                         → skills/web_search.py
  🌤️ Thời tiết + chất lượng không khí                            → skills/weather.py
  📰 Tin tức nhanh từ 5 nguồn báo                                → skills/news.py
  🖼️ OCR ảnh/PDF + dịch hai chiều Anh↔Việt                       → skills/ocr.py, handlers/media_handler.py
  🎙️ Voice: STT (faster-whisper/Groq) + TTS (Piper/gTTS)         → skills/voice.py, handlers/voice_handler.py
  🧠 Suy luận ẩn + trí nhớ dài hạn + persona                      → reasoning.py
  🛠️ Dashboard nút bấm (inline keyboard)                         → handlers/dashboard_handler.py
  🖥️ Lệnh quản trị server (chỉ ADMIN)                            → skills/dashboard.py
  🗂️ Xuất lịch sử hội thoại, /stop, /ping, ...                    → handlers/commands.py

Chạy: python my_bot.py   (cần .env — xem .env.example)
"""

from __future__ import annotations

import httpx
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters,
)

import database as db
import reasoning     # noqa: F401  (nạp trước để SYSTEM_PROMPT_BASE fallback sẵn sàng)
import local_voice    # noqa: F401

from bot_logger import logger
from config import TELEGRAM_TOKEN, OLLAMA_BASE_URL, DEFAULT_MODEL, DB_PATH, ALLOWED_IDS, ADMIN_IDS

import llm_engine
import utils
from skills import web_search as web_search_skill
from skills import weather as weather_skill
from skills import news as news_skill
from skills import dashboard as dashboard_skill

from handlers.text_handler import handle_text
from handlers.voice_handler import handle_voice
from handlers.media_handler import handle_media
from handlers.dashboard_handler import cmd_ui, handle_callback_query
from handlers.commands import (
    cmd_start, cmd_help, cmd_reset, cmd_stop, cmd_export,
    cmd_nickname, cmd_persona, cmd_voice, cmd_stt, cmd_ttsmode,
    cmd_ping, cmd_weather, cmd_news, cmd_autoweb, cmd_shutdown, cmd_reboot,
)


# ═══════════════════════════════════════════════════════════════
# 🚀  Main Setup
# ═══════════════════════════════════════════════════════════════
async def post_init(application: Application):
    http_client = httpx.AsyncClient(follow_redirects=True)

    # Inject HTTP client dùng chung vào các module cần gọi ra internet
    llm_engine.set_http_client(http_client)
    web_search_skill.set_http_client(http_client)
    weather_skill.set_http_client(http_client)
    news_skill.set_http_client(http_client)
    dashboard_skill.set_http_client(http_client)
    application.bot_data["http_client"] = http_client  # giữ tham chiếu để đóng lúc shutdown

    await db.init_db(DB_PATH)
    logger.info(f"🗄️  SQLite sẵn sàng tại: {DB_PATH}")

    try:
        me = await application.bot.get_me()
        utils.BOT_USERNAME = me.username
        logger.info(f"🤖 Bot khởi động với username: @{utils.BOT_USERNAME}")
    except Exception as e:
        logger.warning(f"⚠️ Không lấy được username của bot: {e}")

    models = await llm_engine.get_ollama_models(force=True)
    if not models:
        logger.warning(
            f"⚠️ Không kết nối được Ollama tại {OLLAMA_BASE_URL} — bot vẫn chạy nhưng chat AI sẽ lỗi "
            f"cho tới khi Ollama sẵn sàng."
        )
    elif DEFAULT_MODEL not in models:
        logger.warning(f"⚠️ Model mặc định '{DEFAULT_MODEL}' chưa được cài trong Ollama. Model hiện có: {models}")

    if not ALLOWED_IDS:
        logger.warning(
            "🔓 ALLOWED_USERS đang để TRỐNG — bất kỳ ai trên Telegram cũng dùng được bot này. "
            "Nếu đây không phải chủ đích, hãy khai báo ALLOWED_USERS trong .env."
        )
    if not ADMIN_IDS:
        logger.info("ℹ️ ADMIN_USER_IDS đang để trống — không ai dùng được lệnh quản trị server.")

    from telegram import BotCommand
    commands = [
        BotCommand("start",    "Khởi động bot"),
        BotCommand("help",     "📖 Xem hướng dẫn sử dụng đầy đủ"),
        BotCommand("ui",       "🛠 Mở Dashboard UI Đa cấp trung tâm"),
        BotCommand("weather",  "🌤️ Thời tiết theo thành phố — vd: /weather Hà Nội"),
        BotCommand("news",     "📰 Tin tức nhanh — vd: /news tuoitre"),
        BotCommand("nickname", "👤 Đặt tên gọi riêng"),
        BotCommand("stt",      "🎙️ Chọn engine nghe giọng nói (local/groq)"),
        BotCommand("ttsmode",  "🔊 Bật/tắt trả lời kèm voice note (off/smart/always)"),
        BotCommand("export",   "🗂️ Xuất lịch sử hội thoại"),
        BotCommand("stop",     "🚫 Dừng phản hồi đang tạo"),
        BotCommand("reset",    "♻ Reset toàn bộ lịch sử chat"),
        BotCommand("autoweb",  "🌐 Bật/tắt tự động tìm kiếm cho MỌI tin nhắn"),
        BotCommand("ping",     "🏓 Kiểm tra kết nối Ollama"),
        BotCommand("shutdown", "🛑 [Admin] Tắt nguồn server (cần xác nhận)"),
        BotCommand("reboot",   "🔁 [Admin] Khởi động lại server (cần xác nhận)"),
    ]
    await application.bot.set_my_commands(commands)


async def post_shutdown(application: Application):
    http_client = application.bot_data.get("http_client")
    if http_client is not None:
        await http_client.aclose()
    await db.close_db()
    web_search_skill.shutdown_executor()


async def global_error_handler(update: object, ctx: ContextTypes.DEFAULT_TYPE):
    logger.error(f"⚠️ Lỗi không xử lý được: {ctx.error}", exc_info=ctx.error)
    try:
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ Đã có lỗi xảy ra khi xử lý yêu cầu. Vui lòng thử lại hoặc đổi cách hỏi khác."
            )
    except Exception:
        pass


def main():
    # concurrent_updates(True): mỗi update chạy trong 1 Task riêng (song song), cần thiết để
    # /stop hoạt động đúng trong lúc bot đang stream câu trả lời cho update khác.
    app = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .concurrent_updates(True)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )
    app.add_error_handler(global_error_handler)

    app.add_handler(CallbackQueryHandler(handle_callback_query))
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("ui", cmd_ui))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("export", cmd_export))
    app.add_handler(CommandHandler("nickname", cmd_nickname))
    app.add_handler(CommandHandler("persona", cmd_persona))
    app.add_handler(CommandHandler("voice", cmd_voice))
    app.add_handler(CommandHandler("stt", cmd_stt))
    app.add_handler(CommandHandler("ttsmode", cmd_ttsmode))
    app.add_handler(CommandHandler("ping", cmd_ping))
    app.add_handler(CommandHandler("weather", cmd_weather))
    app.add_handler(CommandHandler("news", cmd_news))
    app.add_handler(CommandHandler("autoweb", cmd_autoweb))
    app.add_handler(CommandHandler("shutdown", cmd_shutdown))
    app.add_handler(CommandHandler("reboot", cmd_reboot))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, handle_media))

    logger.info("🚀 Bot đang khởi động...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
