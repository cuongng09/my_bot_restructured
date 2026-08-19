"""
handlers/media_handler.py — Xử lý ảnh & tài liệu: OCR trích chữ, tự nhận diện Anh/Việt, dịch.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from bot_logger import logger
from config import MAX_UPLOAD_MB
from llm_engine import chat_with_llm
from skills.ocr import process_vision_translation
from utils import (
    is_allowed, is_addressed_in_group, is_rate_limited,
    notify_rate_limited, safe_reply, get_user_model,
)


async def handle_media(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Xử lý ảnh & tài liệu: OCR + dịch tự động."""
    uid = update.effective_user.id
    if not is_allowed(uid) or not is_addressed_in_group(update):
        return
    if await is_rate_limited(uid):
        return await notify_rate_limited(update)

    msg = update.message
    await update.effective_chat.send_action(ChatAction.TYPING)

    tmp_path, is_pdf = None, False
    try:
        if msg.photo:
            tg_file = await ctx.bot.get_file(msg.photo[-1].file_id)
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                tmp_path = tmp.name
            await tg_file.download_to_drive(tmp_path)

        elif msg.document:
            doc  = msg.document
            mime = (doc.mime_type or "").lower()
            fname = (doc.file_name or "").lower()
            size_mb = (doc.file_size or 0) / (1024 * 1024)

            if size_mb > MAX_UPLOAD_MB:
                return await safe_reply(
                    update,
                    f"⚠️ File quá lớn ({size_mb:.1f}MB). Giới hạn hiện tại: {MAX_UPLOAD_MB}MB.",
                )
            if mime.startswith("image/") or fname.endswith((".jpg", ".jpeg", ".png", ".webp", ".bmp")):
                tg_file = await ctx.bot.get_file(doc.file_id)
                suffix = Path(fname).suffix or ".jpg"
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                    tmp_path = tmp.name
                await tg_file.download_to_drive(tmp_path)
            elif mime == "application/pdf" or fname.endswith(".pdf"):
                tg_file = await ctx.bot.get_file(doc.file_id)
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    tmp_path = tmp.name
                await tg_file.download_to_drive(tmp_path)
                is_pdf = True
            else:
                return await safe_reply(
                    update,
                    "⚠️ Chỉ hỗ trợ OCR/dịch cho **ảnh** (jpg/png/webp) hoặc **PDF có lớp text**.",
                )
        else:
            return

        await safe_reply(update, "🔍 Đang OCR & dịch, vui lòng đợi...")
        result = await process_vision_translation(
            tmp_path, uid=uid, is_pdf=is_pdf,
            chat_fn=chat_with_llm, get_model_fn=get_user_model,
        )
        await safe_reply(update, result)

    except Exception as e:
        logger.error(f"⚠️ Lỗi xử lý media: {e}", exc_info=e)
        await safe_reply(update, f"❌ Lỗi xử lý ảnh/tài liệu: {e}")
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)
