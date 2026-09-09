"""
local_voice.py — Voice pipeline LOCAL cho my_bot.py:
  STT: Voicebox (https://github.com/jamiepine/voicebox.git) chạy trên Docker, kết nối qua REST API /transcribe
  TTS: Piper TTS — engine giọng nói neural nhẹ, chạy CPU tốt, hỗ trợ tiếng Việt,
       hoàn toàn offline sau khi tải file model giọng (.onnx + .onnx.json).

Cài đặt (trên máy chạy bot):
    pip install piper-tts
    Docker container Voicebox: docker compose up -d --build (tại thư mục voicebox/)

Tải model / Cấu hình:
  1) Voicebox STT: Chạy qua Docker (mặc định http://127.0.0.1:17600), tự động tải model Whisper
     theo cấu hình VOICEBOX_MODEL (ví dụ: "small", "base", "turbo").
  2) Piper TTS: Cần file giọng tiếng Việt (.onnx + .onnx.json) trong ./voices/
     và khai báo qua biến PIPER_VOICE_PATHS trong .env.

Biến môi trường liên quan (.env):
    VOICEBOX_URL=http://127.0.0.1:17600
    VOICEBOX_MODEL=small
    VOICEBOX_LANGUAGE=vi
    PIPER_VOICE_PATHS=nu:./voices/vi_VN-vais1000-medium.onnx,nam:./voices/vi_VN-25hours_single-low.onnx
    PIPER_DEFAULT_VOICE=nu
"""

import os
import subprocess
import tempfile
import logging
from pathlib import Path
from typing import Optional

import httpx
from config import VOICEBOX_URL, VOICEBOX_MODEL, VOICEBOX_LANGUAGE

logger = logging.getLogger("my_bot.local_voice")

# ── STT: Voicebox (Docker REST API) ──────────────────────────────
def transcribe_audio_local(ogg_path: str) -> str:
    """Gửi file âm thanh tới Voicebox (https://github.com/jamiepine/voicebox.git) chạy Docker
    để nhận diện giọng nói (STT) qua endpoint POST /transcribe.
    CÙNG chữ ký hàm (sync, nhận path .ogg, trả về text)."""
    wav_path = ogg_path.replace(".ogg", ".wav")
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", ogg_path, "-ar", "16000", "-ac", "1", wav_path],
            check=True, capture_output=True,
        )
        url = f"{VOICEBOX_URL.rstrip('/')}/transcribe"
        with open(wav_path, "rb") as af:
            files = {"file": (os.path.basename(wav_path), af, "audio/wav")}
            data = {}
            if VOICEBOX_LANGUAGE:
                data["language"] = VOICEBOX_LANGUAGE
            if VOICEBOX_MODEL:
                data["model"] = VOICEBOX_MODEL

            with httpx.Client(timeout=60.0) as client:
                res = client.post(url, files=files, data=data)

        if res.status_code == 200:
            result = res.json()
            text = result.get("text", "").strip()
            return text or "[Lỗi âm thanh: không nhận diện được nội dung]"
        elif res.status_code == 202:
            return "[Lỗi âm thanh: Voicebox đang tải model Whisper lần đầu, vui lòng thử lại sau]"
        else:
            return f"[Lỗi âm thanh: Voicebox HTTP {res.status_code} - {res.text}]"

    except FileNotFoundError:
        return "[Lỗi âm thanh: chưa cài ffmpeg — cần ffmpeg trong PATH]"
    except (httpx.ConnectError, httpx.NetworkError):
        return f"[Lỗi âm thanh: Không thể kết nối tới Voicebox tại {VOICEBOX_URL}. Hãy đảm bảo container Voicebox đang chạy]"
    except httpx.TimeoutException:
        return "[Lỗi âm thanh: Hết thời gian chờ phản hồi từ Voicebox (timeout)]"
    except Exception as e:
        return f"[Lỗi âm thanh: {e}]"
    finally:
        for p in [ogg_path, wav_path]:
            Path(p).unlink(missing_ok=True)


# ── TTS: Piper ───────────────────────────────────────────────────
def _parse_voice_paths() -> dict[str, str]:
    raw = os.getenv("PIPER_VOICE_PATHS", "")
    out = {}
    for item in raw.split(","):
        item = item.strip()
        if not item or ":" not in item:
            continue
        name, path = item.split(":", 1)
        out[name.strip()] = path.strip()
    return out


VOICE_PATHS = _parse_voice_paths()
DEFAULT_VOICE = os.getenv("PIPER_DEFAULT_VOICE", next(iter(VOICE_PATHS), ""))

_piper_voice_cache: dict[str, object] = {}


def list_available_voices() -> list[str]:
    return list(VOICE_PATHS.keys())


def _get_piper_voice(voice_name: str):
    from piper import PiperVoice  # import trễ
    path = VOICE_PATHS.get(voice_name)
    if not path or not Path(path).exists():
        raise FileNotFoundError(f"Không tìm thấy model giọng Piper cho '{voice_name}' (path: {path})")
    if voice_name not in _piper_voice_cache:
        logger.info(f"🗣️ Đang nạp giọng Piper '{voice_name}' từ {path}...")
        _piper_voice_cache[voice_name] = PiperVoice.load(path)
    return _piper_voice_cache[voice_name]


def prepare_text_for_tts(text: str) -> str:
    """Làm sạch văn bản trước khi đưa vào TTS — chỉ loại bỏ link/đường dẫn URL."""
    import re as _re
    if not text:
        return ""
    clean_text = _re.sub(r'https?://\S+', '', text)
    return clean_text.strip()


def text_to_speech_ogg_local(text: str, voice: Optional[str] = None, speed: float = 1.0) -> Optional[str]:
    """Thay thế text_to_speech_ogg() gốc (gTTS) — chữ ký mở rộng (thêm voice/speed có default),
    vẫn tương thích khi gọi kiểu cũ text_to_speech_ogg_local(text).
    speed: 1.0 = bình thường, <1.0 = nhanh hơn, >1.0 = chậm hơn (Piper dùng length_scale ngược)."""
    clean = prepare_text_for_tts(text)
    if not clean:
        return None
    voice_name = voice or DEFAULT_VOICE
    if not voice_name:
        logger.warning("⚠️ Chưa cấu hình PIPER_VOICE_PATHS — không thể tạo giọng nói local.")
        return None
    try:
        piper_voice = _get_piper_voice(voice_name)
        wav_path = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
        length_scale = max(0.5, min(2.0, speed))
        with open(wav_path, "wb") as wf:
            piper_voice.synthesize(clean, wf, length_scale=length_scale)

        ogg_path = wav_path.replace(".wav", ".ogg")
        subprocess.run(
            ["ffmpeg", "-y", "-i", wav_path, "-c:a", "libopus", ogg_path],
            check=True, capture_output=True,
        )
        Path(wav_path).unlink(missing_ok=True)
        return ogg_path
    except ImportError:
        logger.warning("⚠️ Chưa cài piper-tts — chạy `pip install piper-tts`.")
        return None
    except Exception as e:
        logger.warning(f"⚠️ Lỗi tạo giọng nói TTS (Piper): {e}")
        return None
