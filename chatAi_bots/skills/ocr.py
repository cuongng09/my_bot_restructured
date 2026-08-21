"""
skills/ocr.py — OCR ảnh/PDF + tự nhận diện ngôn ngữ (Anh/Việt) + dịch hai chiều.
Dùng Tesseract (qua pytesseract) + Google Translate (deep_translator).
"""

from __future__ import annotations

import asyncio
import re
from typing import Optional

from PIL import Image, ImageEnhance
import pytesseract
from pypdf import PdfReader
from deep_translator import GoogleTranslator

from bot_logger import logger
from config import TESSERACT_CMD, OCR_LANG

pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

_OCR_LANG_COMBINED = OCR_LANG
_ocr_lang_warned = False

# ── Language detection ─────────────────────────────────────────────────────────
_VN_DIACRITICS_RE = re.compile(
    "[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ"
    "ÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ]"
)


def detect_language(text: str) -> str:
    """Trả về 'vi' hoặc 'en'. Ưu tiên langdetect, fallback bằng heuristic dấu tiếng Việt."""
    sample = text.strip()[:2000]
    if not sample:
        return "en"
    try:
        from langdetect import detect as _ld_detect
        lang = _ld_detect(sample)
        if lang in ("vi", "en"):
            return lang
    except Exception:
        pass
    return "vi" if _VN_DIACRITICS_RE.search(sample) else "en"


# ── OCR ───────────────────────────────────────────────────────────────────────
def _ocr_image_sync(image_path: str, enhance_vi: bool = True) -> str:
    global _ocr_lang_warned
    img = Image.open(image_path)
    if enhance_vi:
        img = img.convert("L")
        w, h = img.size
        img = img.resize((w * 2, h * 2), Image.Resampling.LANCZOS)
        img = ImageEnhance.Contrast(img).enhance(2.0)
        img = ImageEnhance.Sharpness(img).enhance(1.5)
        lang_to_use = _OCR_LANG_COMBINED
    else:
        if img.mode != "RGB":
            img = img.convert("RGB")
        lang_to_use = "eng"
    custom_config = r'--psm 6'
    try:
        return pytesseract.image_to_string(img, lang=lang_to_use, config=custom_config).strip()
    except pytesseract.TesseractError as e:
        if not _ocr_lang_warned:
            logger.warning(f"⚠️ Lỗi OCR gói '{lang_to_use}' ({e}) — Rơi về 'eng'.")
            _ocr_lang_warned = True
        return pytesseract.image_to_string(img, lang="eng", config=custom_config).strip()


def _ocr_pdf_sync(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    texts = []
    for page in reader.pages[:10]:
        t = page.extract_text() or ""
        if t.strip():
            texts.append(t.strip())
    return "\n\n".join(texts)


async def ocr_extract_text(file_path: str, is_pdf: bool = False, enhance_vi: bool = True) -> str:
    loop = asyncio.get_event_loop()
    if is_pdf:
        return await loop.run_in_executor(None, _ocr_pdf_sync, file_path)
    return await loop.run_in_executor(None, _ocr_image_sync, file_path, enhance_vi)


# ── Translation ────────────────────────────────────────────────────────────────
async def translate_text_auto(text: str, source: str, target: str) -> str:
    loop = asyncio.get_event_loop()

    def _tr():
        chunk = text[:4500]
        return GoogleTranslator(source=source, target=target).translate(chunk)

    try:
        return await loop.run_in_executor(None, _tr)
    except Exception as e:
        return f"❌ Lỗi dịch: {e}"


def perform_translation(text: str, direction: str) -> str:
    """Dịch đồng bộ — dùng cho text_trans từ callback."""
    try:
        source = 'en' if 'en_vi' in direction else 'vi'
        target = 'vi' if 'en_vi' in direction else 'en'
        return GoogleTranslator(source=source, target=target).translate(text)
    except Exception as e:
        return f"❌ Lỗi dịch thuật (Google): {e}"


async def repair_vietnamese_diacritics_with_llm(raw_text: str, uid: int, chat_fn, get_model_fn) -> str:
    """Dùng LLM local khôi phục dấu tiếng Việt bị mất do OCR."""
    prompt = [{
        "role": "user",
        "content": (
            "Dưới đây là văn bản tiếng Việt bị mất dấu hoặc sai chính tả do lỗi trích xuất OCR. "
            "Hãy khôi phục lại đúng văn bản tiếng Việt chuẩn, đầy đủ dấu câu và đúng ngữ pháp. "
            "CHỈ TRẢ VỀ VĂN BẢN TIẾNG VIỆT ĐÃ SỬA DẤU, KHÔNG GIẢI THÍCH THÊM.\n\n"
            f"Văn bản OCR thô:\n{raw_text}"
        ),
    }]
    model = await get_model_fn(uid)
    repaired = await chat_fn(prompt, model=model)
    return repaired if repaired and not repaired.startswith("❌") else raw_text


async def process_vision_translation(file_path: str, uid: int = 0, is_pdf: bool = False,
                                     chat_fn=None, get_model_fn=None) -> str:
    """
    Pipeline OCR & Dịch thuật:
    - Tiếng Việt (VI → EN): tiền xử lý ảnh + LLM phục hồi dấu → dịch sang Anh.
    - Tiếng Anh (EN → VI): bỏ qua tiền xử lý nặng → dịch trực tiếp sang Việt.
    """
    raw_text = await ocr_extract_text(file_path, is_pdf=is_pdf, enhance_vi=True)

    if not raw_text or len(raw_text.strip()) < 2:
        kind = "tài liệu PDF (có thể là bản scan ảnh)" if is_pdf else "ảnh"
        return f"❓ Không trích được chữ nào từ {kind}. Hãy thử ảnh rõ nét hơn."

    detected = detect_language(raw_text)

    if detected == "vi":
        if chat_fn and get_model_fn:
            clean_text = await repair_vietnamese_diacritics_with_llm(raw_text, uid, chat_fn, get_model_fn)
        else:
            clean_text = raw_text
        translated = await translate_text_auto(clean_text, source="vi", target="en")
        raw_preview = clean_text[:1200] + ("…" if len(clean_text) > 1200 else "")
        return (
            f"🖼️ **Văn bản gốc (Tiếng Việt — Đã khôi phục dấu):**\n```\n{raw_preview}\n```\n\n"
            f"🇬🇧 **Bản dịch Tiếng Anh:**\n{translated}"
        )
    else:
        if not is_pdf:
            raw_text = await ocr_extract_text(file_path, is_pdf=False, enhance_vi=False)
        translated = await translate_text_auto(raw_text, source="en", target="vi")
        raw_preview = raw_text[:1200] + ("…" if len(raw_text) > 1200 else "")
        return (
            f"🖼️ **Văn bản gốc (Tiếng Anh):**\n```\n{raw_preview}\n```\n\n"
            f"🇻🇳 **Bản dịch Tiếng Việt:**\n{translated}"
        )
