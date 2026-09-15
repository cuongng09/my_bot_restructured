"""
skills/pdf_report.py — Skill "Báo cáo AI PDF": Groq lập dàn ý → tìm web bổ sung dữ liệu →
                        Ollama (local) mở rộng chi tiết từng phần → render PDF (ReportLab).

Chuyển thể từ bot_ai.py (bản gốc xuất PPTX bằng Groq+Ollama hybrid) — giữ đúng tinh thần
"Groq cho lên ý tưởng / Ollama cho mở rộng nội dung, tiết kiệm token", chỉ đổi bước render
cuối cùng từ python-pptx sang ReportLab để xuất file .pdf thay vì .pptx.

Không có Groq (GROQ_API_KEY trống)? Skill tự động dùng chính Ollama cho cả bước lập dàn ý,
vẫn hoạt động bình thường — chỉ chậm hơn một chút.

Cài đặt thêm:  pip install reportlab
Font tiếng Việt: tải NotoSans-Regular.ttf + NotoSans-Bold.ttf (Google Fonts) vào ./fonts/,
                 hoặc trỏ PDF_FONT_PATH / PDF_FONT_BOLD_PATH trong .env tới font khác có dấu.
"""

from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, ListFlowable, ListItem, PageBreak,
    )
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    colors = None
    A4 = None
    ParagraphStyle = None
    cm = None
    pdfmetrics = None
    TTFont = None
    SimpleDocTemplate = None
    Paragraph = None
    Spacer = None
    Table = None
    TableStyle = None
    ListFlowable = None
    ListItem = None
    PageBreak = None

from bot_logger import logger
from config import (
    GROQ_API_KEY, GROQ_MODEL, DEFAULT_MODEL,
    PDF_OUTPUT_DIR, PDF_FONT_PATH, PDF_FONT_BOLD_PATH,
    PDF_MAX_SECTIONS, PDF_NUM_WEB_RESULTS,
)
from llm_engine import chat_with_llm

Path(PDF_OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

if not REPORTLAB_AVAILABLE:
    logger.warning("⚠️ Thư viện 'reportlab' chưa được cài — tính năng xuất báo cáo PDF bị tạm tắt. Cài đặt bằng: pip install reportlab")

groq_client = None
if GROQ_API_KEY:
    try:
        from groq import Groq
        groq_client = Groq(api_key=GROQ_API_KEY)
    except ImportError:
        logger.warning("⚠️ Groq SDK chưa được cài — bỏ qua, skill PDF sẽ dùng Ollama cho cả bước lập dàn ý.")


# ═══════════════════════════════════════════════════════════════
# 1. TÌM WEB BỔ SUNG DỮ LIỆU (dùng lại DDGS đã có trong skills/web_search.py)
# ═══════════════════════════════════════════════════════════════
def _search_web_sync(query: str, max_results: int = 3) -> list[dict]:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        try:
            from ddgs import DDGS
        except ImportError:
            return []
    try:
        with DDGS() as ddgs:
            return [
                {"title": r.get("title", ""), "body": r.get("body", "")}
                for r in ddgs.text(query, region="vn-vi", max_results=max_results)
            ]
    except Exception as e:
        logger.warning(f"⚠️ Lỗi tìm web cho báo cáo PDF: {e}")
        return []


def _deep_search_web_sync(topic: str, num_results: int = PDF_NUM_WEB_RESULTS) -> str:
    """Gộp nhiều truy vấn phụ để có bối cảnh phong phú hơn, giống deep_search_web() gốc."""
    queries = [
        f"{topic} số liệu mới nhất",
        f"{topic} giải pháp xu hướng",
        f"{topic} thách thức rủi ro",
    ]
    combined = []
    for q in queries:
        for r in _search_web_sync(q, max_results=2):
            if r["title"] or r["body"]:
                combined.append(f"• [{r['title']}]: {r['body']}")
    return "\n".join(combined[:num_results]) or "Không tìm thấy dữ liệu bổ sung."


async def deep_search_web(topic: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _deep_search_web_sync, topic)


# ═══════════════════════════════════════════════════════════════
# 2. TIỆN ÍCH JSON
# ═══════════════════════════════════════════════════════════════
def clean_json_response(raw_text: str) -> Any:
    if not raw_text:
        raise ValueError("Phản hồi từ AI rỗng.")
    cleaned = re.sub(r"```(?:json)?", "", raw_text).replace("```", "").strip()
    try:
        return json.loads(cleaned)
    except Exception:
        match = re.search(r"(\[.*\]|\{.*\})", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
    raise ValueError("Không thể bóc tách JSON hợp lệ từ phản hồi AI.")


# ═══════════════════════════════════════════════════════════════
# 3. LẬP DÀN Ý (Groq nếu có, fallback Ollama)
# ═══════════════════════════════════════════════════════════════
def _call_groq_sync(prompt: str) -> str:
    resp = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": "You are a professional strategic AI consultant. "
                                          "Always reply in valid JSON format when requested."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_completion_tokens=4096,
        response_format={"type": "json_object"},
    )
    return (resp.choices[0].message.content or "").strip()


_OUTLINE_PROMPT_TMPL = """Bạn là chuyên gia phân tích & viết báo cáo cấp cao. Dựa trên chủ đề và dữ liệu
thực tế bên dưới, hãy lập DÀN Ý cho một bản BÁO CÁO PDF chuyên nghiệp.

CHỦ ĐỀ: "{topic}"

DỮ LIỆU THỰC TẾ THU THẬP ĐƯỢC (bám sát, trích số liệu/luận điểm cụ thể khi phù hợp):
{web_context}

YÊU CẦU:
1. Từ 6 đến {max_sections} phần (không tính trang bìa), đủ để triển khai trọn vẹn chủ đề:
   bối cảnh → phân tích/giải pháp → số liệu → rủi ro → kết luận & khuyến nghị.
2. Mỗi phần có "title" (tiêu đề ngắn gọn, cụ thể — KHÔNG chung chung) và "summary"
   (1-2 câu định hướng nội dung phần đó, có luận điểm/số liệu cụ thể nếu có).
3. Trả về ĐÚNG JSON sau, không thêm giải thích:
{{
  "report_title": "Tiêu đề báo cáo tổng thể, bám sát chủ đề",
  "sections": [
    {{"title": "Tiêu đề phần 1", "summary": "Định hướng nội dung cụ thể"}}
  ]
}}"""


async def generate_outline(topic: str, web_context: str, model: str = DEFAULT_MODEL) -> dict:
    prompt = _OUTLINE_PROMPT_TMPL.format(topic=topic, web_context=web_context, max_sections=PDF_MAX_SECTIONS)

    if groq_client:
        loop = asyncio.get_event_loop()
        try:
            raw = await loop.run_in_executor(None, _call_groq_sync, prompt)
            data = clean_json_response(raw)
            if isinstance(data, dict) and data.get("sections"):
                return data
        except Exception as e:
            logger.warning(f"⚠️ Groq lập dàn ý lỗi ({e}) — chuyển sang dùng Ollama.")

    # Fallback: dùng chính Ollama cho bước lập dàn ý
    raw = await chat_with_llm([{"role": "user", "content": prompt}], model)
    try:
        data = clean_json_response(raw)
    except Exception:
        data = {}
    if not isinstance(data, dict) or not data.get("sections"):
        # Fallback cuối cùng: dàn ý tối giản cố định, đảm bảo báo cáo vẫn tạo được
        data = {
            "report_title": topic,
            "sections": [
                {"title": "Bối cảnh & Tổng quan", "summary": f"Tổng quan thực trạng về {topic}."},
                {"title": "Phân tích & Giải pháp", "summary": "Các hướng tiếp cận, giải pháp chính."},
                {"title": "Số liệu & Bằng chứng", "summary": "Dữ liệu, số liệu minh chứng liên quan."},
                {"title": "Rủi ro & Thách thức", "summary": "Những rủi ro cần lưu ý và cách giảm thiểu."},
                {"title": "Kết luận & Khuyến nghị", "summary": "Tổng kết và đề xuất hành động."},
            ],
        }
    return data


# ═══════════════════════════════════════════════════════════════
# 4. MỞ RỘNG CHI TIẾT TỪNG PHẦN (Ollama local — tiết kiệm token Groq)
# ═══════════════════════════════════════════════════════════════
_SECTION_PROMPT_TMPL = """Bạn là chuyên gia biên tập nội dung báo cáo cao cấp. Hãy MỞ RỘNG chi tiết,
bám sát thực tế cho PHẦN báo cáo dưới đây — không viết chung chung, ưu tiên dữ kiện/số liệu/
luận điểm cụ thể lấy từ BỐI CẢNH khi có thể.

CHỦ ĐỀ BÁO CÁO: "{topic}"
PHẦN CẦN MỞ RỘNG: {title} — {summary}
BỐI CẢNH THỰC TẾ: {web_context}

Trả về DUY NHẤT 1 JSON object hợp lệ, không kèm giải thích/markdown, đúng cấu trúc:
{{
  "analysis": "Đoạn phân tích 100-180 từ, mạch lạc, cụ thể, KHÔNG lặp lại nguyên văn tiêu đề",
  "bullets": ["Luận điểm/số liệu cụ thể 1", "Luận điểm/số liệu cụ thể 2", "Luận điểm/số liệu cụ thể 3"]
}}"""


async def expand_section(topic: str, section: dict, web_context: str, model: str) -> dict:
    prompt = _SECTION_PROMPT_TMPL.format(
        topic=topic, title=section.get("title", ""), summary=section.get("summary", ""),
        web_context=web_context,
    )
    try:
        raw = await chat_with_llm([{"role": "user", "content": prompt}], model)
        data = clean_json_response(raw)
        if not isinstance(data, dict):
            raise ValueError("Không phải JSON object")
    except Exception as e:
        logger.warning(f"⚠️ Ollama mở rộng phần '{section.get('title')}' lỗi ({e}) — dùng tóm tắt gốc.")
        data = {"analysis": section.get("summary", ""), "bullets": []}

    data.setdefault("analysis", section.get("summary", ""))
    if not isinstance(data.get("bullets"), list):
        data["bullets"] = []
    return {**section, **data}


async def expand_all_sections(topic: str, sections: list[dict], web_context: str, model: str) -> list[dict]:
    # Giới hạn song song để không quá tải Ollama local (giống max_workers=3 của bản gốc)
    sem = asyncio.Semaphore(3)

    async def _one(sec: dict) -> dict:
        async with sem:
            return await expand_section(topic, sec, web_context, model)

    return await asyncio.gather(*[_one(s) for s in sections])


# ═══════════════════════════════════════════════════════════════
# 5. RENDER PDF (ReportLab)
# ═══════════════════════════════════════════════════════════════
_FONT_NAME, _FONT_BOLD = "Helvetica", "Helvetica-Bold"  # fallback mặc định (không dấu tiếng Việt)
_fonts_registered = False


def _register_fonts():
    """Đăng ký font Unicode (Noto Sans) nếu có sẵn — cần để hiển thị đúng dấu tiếng Việt.
    Nếu không tìm thấy font, PDF vẫn tạo được nhưng ký tự có dấu có thể hiển thị sai."""
    global _FONT_NAME, _FONT_BOLD, _fonts_registered
    if _fonts_registered:
        return
    _fonts_registered = True
    reg_path, bold_path = Path(PDF_FONT_PATH), Path(PDF_FONT_BOLD_PATH)
    if reg_path.exists():
        try:
            pdfmetrics.registerFont(TTFont("NotoSans", str(reg_path)))
            _FONT_NAME = "NotoSans"
            if bold_path.exists():
                pdfmetrics.registerFont(TTFont("NotoSans-Bold", str(bold_path)))
                _FONT_BOLD = "NotoSans-Bold"
            else:
                _FONT_BOLD = "NotoSans"
        except Exception as e:
            logger.warning(f"⚠️ Lỗi nạp font PDF '{reg_path}': {e} — dùng font mặc định (có thể lỗi dấu).")
    else:
        logger.warning(
            f"⚠️ Không tìm thấy font '{reg_path}' — tiếng Việt có dấu có thể hiển thị sai trong PDF. "
            f"Tải NotoSans-Regular.ttf/NotoSans-Bold.ttf vào thư mục fonts/ để khắc phục."
        )


def _build_pdf_sync(report_title: str, topic: str, sections: list[dict], filepath: Path) -> Path:
    _register_fonts()

    styles = {
        "cover_title": ParagraphStyle(
            "cover_title", fontName=_FONT_BOLD, fontSize=26, leading=32,
            textColor=colors.HexColor("#0F172A"), spaceAfter=14, alignment=1,
        ),
        "cover_sub": ParagraphStyle(
            "cover_sub", fontName=_FONT_NAME, fontSize=13, leading=18,
            textColor=colors.HexColor("#64748B"), alignment=1,
        ),
        "h1": ParagraphStyle(
            "h1", fontName=_FONT_BOLD, fontSize=17, leading=22,
            textColor=colors.HexColor("#0F172A"), spaceBefore=6, spaceAfter=10,
            borderColor=colors.HexColor("#06B6D4"), borderWidth=0,
        ),
        "body": ParagraphStyle(
            "body", fontName=_FONT_NAME, fontSize=11, leading=16,
            textColor=colors.HexColor("#1E293B"), spaceAfter=8, alignment=4,  # justify
        ),
        "bullet": ParagraphStyle(
            "bullet", fontName=_FONT_NAME, fontSize=10.5, leading=15,
            textColor=colors.HexColor("#334155"),
        ),
        "footer": ParagraphStyle(
            "footer", fontName=_FONT_NAME, fontSize=8, textColor=colors.HexColor("#94A3B8"),
        ),
    }

    doc = SimpleDocTemplate(
        str(filepath), pagesize=A4,
        leftMargin=2.2 * cm, rightMargin=2.2 * cm, topMargin=2.4 * cm, bottomMargin=2.2 * cm,
        title=report_title, author="AI Report Generator",
    )

    story = []

    # ── Trang bìa ──
    story.append(Spacer(1, 5 * cm))
    story.append(Paragraph(report_title, styles["cover_title"]))
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph(f"Chủ đề: {topic}", styles["cover_sub"]))
    story.append(Paragraph(datetime.now().strftime("Tạo lúc %H:%M ngày %d/%m/%Y"), styles["cover_sub"]))
    story.append(Spacer(1, 1 * cm))
    line_tbl = Table([[""]], colWidths=[8 * cm], rowHeights=[0.06 * cm])
    line_tbl.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#06B6D4"))]))
    story.append(line_tbl)
    story.append(PageBreak())

    # ── Mục lục đơn giản ──
    story.append(Paragraph("Mục lục", styles["h1"]))
    for i, sec in enumerate(sections, 1):
        story.append(Paragraph(f"{i}. {sec.get('title', '')}", styles["body"]))
    story.append(PageBreak())

    # ── Từng phần nội dung ──
    for i, sec in enumerate(sections, 1):
        story.append(Paragraph(f"{i}. {sec.get('title', '')}", styles["h1"]))
        analysis = (sec.get("analysis") or sec.get("summary") or "").strip()
        if analysis:
            story.append(Paragraph(analysis, styles["body"]))

        bullets = [b for b in (sec.get("bullets") or []) if str(b).strip()]
        if bullets:
            story.append(ListFlowable(
                [ListItem(Paragraph(str(b), styles["bullet"]), leftIndent=6) for b in bullets],
                bulletType="bullet", start="circle", leftIndent=14, spaceBefore=4, spaceAfter=10,
            ))
        story.append(Spacer(1, 6))

    def _footer(canvas, _doc):
        canvas.saveState()
        canvas.setFont(_FONT_NAME, 8)
        canvas.setFillColor(colors.HexColor("#94A3B8"))
        canvas.drawRightString(A4[0] - 2.2 * cm, 1.3 * cm, f"Trang {_doc.page}")
        canvas.drawString(2.2 * cm, 1.3 * cm, "Được tạo tự động bởi AI Report Generator")
        canvas.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return filepath


# ═══════════════════════════════════════════════════════════════
# 6. ORCHESTRATOR — hàm chính gọi từ handler
# ═══════════════════════════════════════════════════════════════
def _safe_filename(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE).strip().lower()
    slug = re.sub(r"[\s_-]+", "_", slug)[:60]
    return slug or "bao_cao"


async def generate_pdf_report(topic: str, model: str = DEFAULT_MODEL, uid: int = 0) -> Path:
    """Pipeline đầy đủ: tìm web → lập dàn ý (Groq/Ollama) → mở rộng chi tiết (Ollama) → render PDF.
    Trả về Path tới file PDF đã tạo trong PDF_OUTPUT_DIR."""
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("Thư viện 'reportlab' chưa được cài đặt. Vui lòng cài đặt bằng: pip install reportlab")

    web_context = await deep_search_web(topic)
    outline = await generate_outline(topic, web_context, model)
    report_title = outline.get("report_title") or topic
    sections = outline.get("sections") or []
    if not isinstance(sections, list) or not sections:
        raise RuntimeError("Không lập được dàn ý báo cáo — thử lại hoặc đổi chủ đề cụ thể hơn.")

    sections = await expand_all_sections(topic, sections, web_context, model)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{_safe_filename(topic)}_{timestamp}.pdf"
    filepath = Path(PDF_OUTPUT_DIR) / filename

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _build_pdf_sync, report_title, topic, sections, filepath)
