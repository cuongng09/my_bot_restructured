"""
local_voice.py — Voice pipeline HOÀN TOÀN LOCAL cho my_bot.py, thay thế Groq Whisper (STT)
và gTTS (TTS), vốn cả hai đều cần gọi ra internet/API ngoài.

  STT: faster-whisper (CTranslate2)  — chạy CPU hoặc GPU, không cần key, không cần internet
       sau khi đã tải model 1 lần đầu.
  TTS: Piper TTS                      — engine giọng nói neural nhẹ, chạy CPU tốt, hỗ trợ tiếng Việt,
       hoàn toàn offline sau khi tải file model giọng (.onnx + .onnx.json).

Cài đặt (trên máy chạy bot):
    pip install faster-whisper piper-tts

Tải model:
  1) faster-whisper: KHÔNG cần tải tay — lần đầu chạy sẽ tự tải model (vd "small") vào cache
     local (~/.cache/huggingface). Sau đó chạy hoàn toàn offline.
     Nếu máy không có internet lúc đầu, tải trước bằng:
         from faster_whisper import download_model
         download_model("small", output_dir="./models/whisper-small")
     rồi trỏ FASTER_WHISPER_MODEL=./models/whisper-small trong .env

  2) Piper — cần tải file giọng tiếng Việt (.onnx + .onnx.json), ví dụ giọng "vi_VN-vais1000-medium"
     từ kho model chính thức của Piper (rhasspy/piper-voices). Đặt 2 file vào thư mục ./voices/
     rồi trỏ đường dẫn qua PIPER_VOICE_PATHS trong .env (xem UPGRADE_GUIDE.md).

Biến môi trường liên quan (.env):
    FASTER_WHISPER_MODEL=small        # tiny/base/small/medium/large-v3, hoặc path model đã tải sẵn
    FASTER_WHISPER_DEVICE=cpu         # cpu | cuda
    FASTER_WHISPER_COMPUTE=int8       # int8 (nhẹ, khuyên dùng cho CPU) | float16 (GPU)
    PIPER_VOICE_PATHS=nu:./voices/vi_VN-vais1000-medium.onnx,nam:./voices/vi_VN-25hours_single-low.onnx
    PIPER_DEFAULT_VOICE=nu
"""

import os
import subprocess
import tempfile
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("my_bot.local_voice")

# ── STT: faster-whisper ──────────────────────────────────────────
_whisper_model = None
_WHISPER_MODEL_NAME = os.getenv("FASTER_WHISPER_MODEL", "small")
_WHISPER_DEVICE = os.getenv("FASTER_WHISPER_DEVICE", "cpu")
_WHISPER_COMPUTE = os.getenv("FASTER_WHISPER_COMPUTE", "int8")


def _get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel  # import trễ để bot vẫn chạy được nếu chưa cài lib
        logger.info(f"🧠 Đang nạp model faster-whisper '{_WHISPER_MODEL_NAME}' ({_WHISPER_DEVICE}/{_WHISPER_COMPUTE})...")
        _whisper_model = WhisperModel(_WHISPER_MODEL_NAME, device=_WHISPER_DEVICE, compute_type=_WHISPER_COMPUTE)
    return _whisper_model


def transcribe_audio_local(ogg_path: str) -> str:
    """Thay thế transcribe_audio() gốc (Groq) — CÙNG chữ ký hàm (sync, nhận path .ogg, trả về text),
    nên chỉ cần đổi tên hàm được gọi trong handle_voice(), không cần sửa gì khác."""
    wav_path = ogg_path.replace(".ogg", ".wav")
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", ogg_path, "-ar", "16000", "-ac", "1", wav_path],
            check=True, capture_output=True,
        )
        model = _get_whisper_model()
        segments, _info = model.transcribe(wav_path, language="vi", beam_size=5, vad_filter=True)
        text = " ".join(seg.text.strip() for seg in segments).strip()
        return text or "[Lỗi âm thanh: không nhận diện được nội dung]"
    except FileNotFoundError:
        return "[Lỗi âm thanh: chưa cài ffmpeg — cần ffmpeg trong PATH]"
    except ImportError:
        return "[Lỗi âm thanh: chưa cài faster-whisper — chạy `pip install faster-whisper`]"
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
    """Giữ nguyên logic làm sạch text như bản gốc (bỏ bảng markdown, link, format số)."""
    import re as _re
    if not text:
        return ""
    lines = text.splitlines()
    filtered_lines = [line for line in lines if not ('|' in line or '---' in line)]
    clean_text = " ".join(filtered_lines)
    clean_text = _re.sub(r'\[\d+\]', '', clean_text)
    clean_text = _re.sub(r'https?://\S+', '', clean_text)
    clean_text = _re.sub(r'[*_`#~]|(- )', ' ', clean_text)
    clean_text = clean_text.split("🔗")[0].strip()

    def _format_number(match):
        num_str = match.group(0)
        try:
            return f"{int(num_str):,}".replace(",", ".")
        except ValueError:
            return num_str

    clean_text = _re.sub(r'\b\d{4,}\b', _format_number, clean_text)
    return _re.sub(r'\s+', ' ', clean_text).strip()


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
