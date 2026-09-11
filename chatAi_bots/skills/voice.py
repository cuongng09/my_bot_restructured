"""
skills/voice.py — Pipeline giọng nói:
  STT: Voicebox Docker (local) hoặc Groq Whisper API (tùy cài đặt /stt của user)
  TTS: Piper TTS (local) với fallback về gTTS (cần internet)
  Tích hợp: xem handle_voice() trong handlers/voice_handler.py
"""

from __future__ import annotations

import asyncio
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import database as db
import local_voice
from bot_logger import logger
from config import GROQ_API_KEY

# Groq client — khởi tạo 1 lần nếu có API key
groq_client = None
if GROQ_API_KEY:
    try:
        from groq import Groq
        groq_client = Groq(api_key=GROQ_API_KEY)
    except ImportError:
        logger.warning("⚠️ Groq SDK chưa được cài — `pip install groq` nếu muốn dùng engine Groq.")


# ── Groq Whisper STT (sync, chạy trong executor) ──────────────────────────────
def transcribe_audio_groq(ogg_path: str) -> str:
    wav_path = ogg_path.replace(".ogg", ".wav")
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", ogg_path, "-ar", "16000", "-ac", "1", wav_path],
            check=True, capture_output=True,
        )
        if not groq_client:
            return "[Lỗi: Chưa cấu hình GROQ_API_KEY trong .env]"
        with open(wav_path, "rb") as af:
            translation = groq_client.audio.transcriptions.create(
                file=(os.path.basename(wav_path), af.read()),
                model="whisper-large-v3",
                language="vi",
            )
        return translation.text.strip()
    except Exception as e:
        return f"[Lỗi âm thanh: {e}]"
    finally:
        for p in [ogg_path, wav_path]:
            Path(p).unlink(missing_ok=True)


def _copy_ogg(ogg_path: str) -> str:
    """Mỗi engine STT tự xóa file .ogg khi xong — cần copy trước khi truyền vào."""
    fd, copy_path = tempfile.mkstemp(suffix=".ogg")
    os.close(fd)
    shutil.copyfile(ogg_path, copy_path)
    return copy_path


async def transcribe_for_user(uid: int, ogg_path: str) -> str:
    """Chọn engine STT theo cài đặt /stt của user; tự fallback nếu engine chính lỗi."""
    loop = asyncio.get_event_loop()
    engine = (await db.get_settings(uid))["stt_engine"] or "local"

    if engine == "groq" and groq_client:
        primary, fallback = transcribe_audio_groq, local_voice.transcribe_audio_local
    else:
        primary = local_voice.transcribe_audio_local
        fallback = transcribe_audio_groq if groq_client else None

    text = await loop.run_in_executor(None, primary, _copy_ogg(ogg_path))
    if text.startswith("[Lỗi") and fallback is not None:
        logger.warning(f"⚠️ STT engine chính lỗi ({text}) — thử fallback...")
        text = await loop.run_in_executor(None, fallback, _copy_ogg(ogg_path))

    Path(ogg_path).unlink(missing_ok=True)
    return text


# ── TTS (gTTS fallback) ────────────────────────────────────────────────────────
def _prepare_text_for_tts(text: str) -> str:
    """Làm sạch văn bản trước khi đưa vào TTS (dùng chung logic chuẩn hoá của local_voice)."""
    return local_voice.prepare_text_for_tts(text)


def text_to_speech_ogg_gtts(text: str) -> Optional[str]:
    """TTS bằng gTTS (cần internet) — dùng làm fallback khi Piper chưa cấu hình."""
    clean = _prepare_text_for_tts(text)
    if not clean:
        return None
    try:
        from gtts import gTTS
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            mp3_path = tmp.name
        gTTS(text=clean, lang='vi', slow=False).save(mp3_path)
        ogg_path = mp3_path.replace(".mp3", ".ogg")
        subprocess.run(
            ["ffmpeg", "-y", "-i", mp3_path, "-c:a", "libopus", ogg_path],
            check=True, capture_output=True,
        )
        Path(mp3_path).unlink(missing_ok=True)
        return ogg_path
    except Exception as e:
        logger.warning(f"⚠️ Lỗi tạo giọng nói gTTS: {e}")
        return None


async def maybe_send_voice_reply(update, uid: int, reply_text: str) -> None:
    """Gửi voice note phản hồi.
    Ưu tiên Piper local; fallback về gTTS nếu Piper chưa cấu hình."""
    settings = await db.get_settings(uid)
    voice_mode = settings.get("voice_mode") or "smart"
    if voice_mode == "off":
        return

    loop = asyncio.get_event_loop()
    voice_name = settings.get("tts_voice") or None
    ogg_path = None

    if local_voice.list_available_voices():
        ogg_path = await loop.run_in_executor(
            None, local_voice.text_to_speech_ogg_local, reply_text, voice_name, 1.0,
        )
    if not ogg_path:
        ogg_path = await loop.run_in_executor(None, text_to_speech_ogg_gtts, reply_text)
    if not ogg_path:
        return

    try:
        with open(ogg_path, "rb") as f:
            await update.effective_chat.send_voice(voice=f)
    except Exception as e:
        logger.warning(f"⚠️ Lỗi gửi voice reply: {e}")
    finally:
        Path(ogg_path).unlink(missing_ok=True)
