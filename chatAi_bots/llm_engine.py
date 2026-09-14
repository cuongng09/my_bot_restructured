"""
llm_engine.py — Giao tiếp với Ollama: model cache, build grounded messages,
                chat_with_llm (non-stream) và chat_with_llm_stream (async generator).
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

import reasoning
from bot_logger import logger
from config import (
    OLLAMA_BASE_URL, OLLAMA_TIMEOUT_SEC, OLLAMA_RETRY_ATTEMPTS, OLLAMA_CONTEXT_SIZE,
    COMPARISON_TRIGGER_KEYWORDS, should_trigger_web_search,
)
from context_manager import default_context_manager, estimate_tokens, estimate_messages_tokens


def get_vietnam_time_str() -> str:
    """Trả về chuỗi thời gian thực hiện tại theo múi giờ Việt Nam (GMT+7)."""
    tz_vn = timezone(timedelta(hours=7))
    now = datetime.now(tz_vn)
    weekday_vn = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"][now.weekday()]
    return now.strftime(f"{weekday_vn}, ngày %d/%m/%Y, %H:%M (GMT+7)")

# HTTP client được inject từ my_bot.post_init (tránh tạo nhiều client)
_http_client = None


def set_http_client(client):
    global _http_client
    _http_client = client


# ── Model cache ────────────────────────────────────────────────────────────────
_MODEL_CACHE = {"ts": 0.0, "models": []}
_MODEL_CACHE_TTL = 20.0


async def get_ollama_models(force: bool = False) -> list[str]:
    now = time.monotonic()
    if not force and (now - _MODEL_CACHE["ts"]) < _MODEL_CACHE_TTL and _MODEL_CACHE["models"]:
        return _MODEL_CACHE["models"]
    try:
        r = await _http_client.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        models = [m["name"] for m in r.json().get("models", [])] if r.status_code == 200 else []
        _MODEL_CACHE["ts"] = now
        _MODEL_CACHE["models"] = models
        return models
    except Exception:
        return _MODEL_CACHE["models"]


# ── Tiền lọc ý định tìm kiếm nhanh (Fast Heuristic Intent Filter) ────────────────
_NON_SEARCH_KEYWORDS = [
    # Chào hỏi, xã giao, cảm ơn ngắn
    r'^(chào|xin chào|hello|hi|alo|hế lô|hé lô|ê|ơi|cảm ơn|thanks|tks|tạm biệt|bye|good morning|ngủ ngon)\b',
    # Lập trình & kỹ thuật
    r'\b(viết code|viết hàm|viết script|sửa code|debug|tối ưu code|giải thuật|thuật toán|python|javascript|typescript|c\+\+|java|c\#|golang|html|css|sql|dockerfile|regex)\b',
    # Toán học, logic
    r'\b(giải phương trình|tính tích phân|tính đạo hàm|chứng minh rằng|bài toán này|đố vui|câu đố logic|phép tính)\b',
    # Sáng tác văn học, thơ ca, dịch thuật
    r'\b(làm\s+(một\s+)?(bài\s+)?thơ|viết\s+(một\s+)?(bài\s+)?thơ|sáng tác thơ|thơ lục bát|viết\s+(một\s+)?(đoạn\s+|bài\s+)?văn|viết\s+(một\s+)?(bài\s+)?báo|viết\s+(một\s+)?(bức\s+)?(thư|email)|kể\s+(một\s+)?câu chuyện|kể chuyện)\b',
    # Tâm sự cảm xúc, triết lý, thông tin về bot
    r'\b(tâm sự|buồn quá|vui quá|bạn nghĩ gì về|ý nghĩa cuộc sống|bạn là ai|bạn tên gì|bạn được tạo ra khi nào)\b',
]
_NON_SEARCH_RE = re.compile("|".join(_NON_SEARCH_KEYWORDS), re.IGNORECASE)


def fast_search_intent_check(text: str) -> Optional[dict]:
    """Kiểm tra nhanh bằng regex các câu hỏi chắc chắn KHÔNG cần search web.
    Giúp phản hồi siêu tốc bằng kiến thức bách khoa AI, không tốn tài nguyên gọi phân loại.
    """
    stripped = text.strip()
    # Các câu chat quá ngắn mang tính chào hỏi, cảm thán
    if len(stripped) <= 15 and re.search(r'^(chào|hi|hello|alo|ok|oke|cảm ơn|thanks|bye|tuyệt|đúng|sai|ừ|uh|vâng)\b', stripped, re.I):
        return {"need_search": False, "query": ""}

    # Nếu khớp các mẫu sáng tạo, code, toán, tâm sự rõ rệt mà không chứa từ khóa thời sự
    from config import WEB_SEARCH_TRIGGER_KEYWORDS_STRONG
    has_strong_trigger = any(kw in stripped.lower() for kw in WEB_SEARCH_TRIGGER_KEYWORDS_STRONG)
    if not has_strong_trigger and _NON_SEARCH_RE.search(stripped):
        return {"need_search": False, "query": ""}

    return None


# ── Web-search decision (LLM tự quyết định, thay cho match từ khóa) ────────────
def _build_search_decision_system() -> str:
    current_time = get_vietnam_time_str()
    return (
        f"Bạn là bộ phân tích truy vấn nội bộ của hệ thống AI. Thời gian thực tế hiện tại: {current_time}.\n"
        "Nhiệm vụ DUY NHẤT:\n"
        "1. Phân tích tin nhắn của người dùng và xác định xem có CẦN và CÓ THỂ tra cứu Internet thời gian thực để trả lời hay không.\n"
        "2. Nếu CẦN, hãy chuyển đổi (reformulate) câu hỏi thành từ khóa tìm kiếm (search query) Google/DuckDuckGo ngắn gọn, tối ưu nhất.\n\n"
        "QUY TẮC PHÂN LOẠI:\n"
        "- KHÔNG CẦN SEARCH (need_search=false):\n"
        "  + Kiến thức bách khoa phổ thông, lý thuyết khoa học cố định (toán, lý, hóa, sinh, lịch sử kinh điển, định nghĩa từ ngữ, ngữ pháp).\n"
        "  + Lập trình, thuật toán, viết code, sửa lỗi, giải thích công nghệ/ngôn ngữ lập trình nói chung.\n"
        "  + Yêu cầu sáng tạo: viết văn, làm thơ, soạn email, dịch thuật, tóm tắt nội dung.\n"
        "  + Chào hỏi, cảm ơn, trò chuyện phiếm, tâm sự cảm xúc, triết lý sống, hỏi về bot/người dùng.\n"
        "  + Lập luận, suy luận logic, giải bài toán, phân tích ý tưởng.\n\n"
        "- CẦN SEARCH (need_search=true):\n"
        "  + Công nghệ cập nhật từng ngày/giờ: mô hình AI mới ra mắt, phần mềm, framework, card đồ họa/chip, tin tức công nghệ mới nhất.\n"
        "  + Dữ liệu biến động theo thời gian: giá cả, giá vàng, tỷ giá ngoại tệ, giá xăng dầu, lãi suất ngân hàng, chứng khoán, tiền số.\n"
        "  + Tin tức, sự kiện thời sự, tình hình xã hội, giải đấu thể thao, kết quả bầu cử gần đây.\n"
        "  + Thông tin về người đang giữ chức vụ/vai trò hiện tại (tổng thống, thủ tướng, chủ tịch, CEO, HLV...).\n"
        "  + Thời tiết hôm nay, dự báo thời tiết.\n"
        "  + Sự kiện, lịch trình diễn ra trong năm nay hoặc tương lai gần.\n\n"
        "QUY TẮC TẠO QUERY (nếu need_search=true):\n"
        "- Chỉ trích xuất 2-6 từ khóa nòng cốt (keywords), tập trung vào tên thực thể công nghệ, sản phẩm, nhân vật hoặc sự kiện chính.\n"
        "- LOẠI BỎ HẾT đại từ, từ xưng hô, câu hỏi tự nhiên (ví dụ: 'bạn ơi', 'cho mình hỏi', 'là gì vậy', 'ai đang làm', 'nhỉ', 'nha', 'thế').\n"
        "- Giữ lại thực thể chính và thời gian nếu có (Ví dụ: 'deepseek v3 mới nhất có gì hot' -> 'deepseek v3 latest update').\n\n"
        "CHỈ trả lời bằng đúng 1 dòng JSON thuần túy, KHÔNG kèm giải thích, KHÔNG dùng markdown/code fence:\n"
        '{"need_search": true hoặc false, "query": "từ khóa tìm kiếm ngắn gọn nếu need_search=true, ngược lại để rỗng"}'
    )


async def decide_web_search(text: str, model: str) -> dict:
    """Hỏi LLM xem tin nhắn `text` có cần tra cứu web thời gian thực hay không và trích xuất query tối ưu.

    Trả về {"need_search": bool, "query": str}.
    """
    # 1. Kiểm tra nhanh bằng bộ lọc Heuristic Intent
    fast_result = fast_search_intent_check(text)
    if fast_result is not None:
        return fast_result

    # 2. Phân loại thông minh bằng LLM
    try:
        r = await _http_client.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": _build_search_decision_system()},
                    {"role": "user", "content": text},
                ],
                "stream": False,
                "options": {"temperature": 0.0, "top_p": 0.9, "num_ctx": 1024, "num_predict": 120},
            },
            timeout=15.0,
        )
        r.raise_for_status()
        raw = r.json()["message"]["content"].strip()

        # Model đôi khi vẫn kèm ```json ... ``` hoặc text thừa quanh JSON — cắt ra phần {...} đầu tiên.
        raw = raw.strip().strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            raw = match.group(0)

        data = json.loads(raw)
        need_search = bool(data.get("need_search", False))
        from skills.web_search import clean_search_query
        query = clean_search_query((data.get("query") or "").strip() or text) if need_search else ""
        return {"need_search": need_search, "query": query}

    except Exception as e:
        logger.warning(
            f"⚠️ Lỗi khi hỏi LLM có cần search web không ({e}) — fallback sang match từ khóa cũ."
        )
        from skills.web_search import clean_search_query
        need = should_trigger_web_search(text)
        return {"need_search": need, "query": clean_search_query(text) if need else ""}


# ── Grounded message builder ───────────────────────────────────────────────────
def _trim_history_for_context(messages: list[dict], *, max_recent_turns: int = 8) -> list[dict]:
    """Giữ chỉ các turn gần nhất để nhường chỗ cho dữ liệu web mới và tránh kéo dài context."""
    if not messages:
        return []
    if len(messages) <= max_recent_turns:
        return messages
    recent = messages[-max_recent_turns:]
    recent.insert(
        0,
        {
            "role": "user",
            "content": "[Lịch sử trò chuyện cũ đã được rút gọn để nhường chỗ cho dữ liệu web mới; chỉ giữ các tin nhắn gần nhất.]",
        },
    )
    return recent


def _truncate_for_context(text: str, limit: int = 12000) -> str:
    if not text:
        return text
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "\n...[cắt ngắn tự động để vừa context]"


def _log_payload_debug(formatted: list[dict], web_context: str) -> None:
    total_chars = sum(len(str(msg.get("content", "") or "")) for msg in formatted)
    logger.info(
        "Ollama payload summary: messages=%d, web_context_chars=%d, total_chars=%d",
        len(formatted), len(web_context or ""), total_chars,
    )
    for idx, msg in enumerate(formatted):
        content = str(msg.get("content", "") or "")
        preview = content.replace("\n", " ")[:220]
        logger.info(
            "Ollama message[%d] role=%s chars=%d preview=%s",
            idx,
            msg.get("role", "unknown"),
            len(content),
            preview,
        )


def clean_model_generated_sources(text: str) -> str:
    """Loại bỏ phần 'Nguồn tham khảo' hoặc danh sách link URL do chính LLM tự sinh ở cuối văn bản,
    để tránh bị trùng lặp với sources_footer do hệ thống đính kèm."""
    if not text:
        return text
    # 1. Tìm và cắt bỏ khối 'Nguồn tham khảo:' hoặc 'Tài liệu tham khảo:' ở cuối
    cleaned = re.sub(
        r'(?i)\n+([#*_\s]*(?:nguồn(?:\s+tham\s+khảo)?|tài liệu(?:\s+tham\s+khảo)?|tham khảo|references|sources)[:\s*]*[\r\n]+(?:[-*•\d.\[]\s*.*[\r\n]*)+)\s*$',
        '',
        text.strip(),
    )
    # 2. Loại bỏ các dòng trần chỉ chứa URL hoặc link ở cuối
    cleaned = re.sub(r'(?i)\n+(?:(?:nguồn|nguồn tham khảo|link)[:\s*]*)?(?:https?://\S+\s*)+$', '', cleaned.strip())
    return cleaned.strip()


def build_grounded_messages(
    messages: list[dict],
    web_context: str = "",
    force_concise: bool = False,
    nickname: Optional[str] = None,
    persona: Optional[str] = None,
    profile_summary: str = "",
) -> list[dict]:
    """
    Xây dựng danh sách messages chuẩn bị gửi cho Ollama.
    Tách biệt: Lịch sử hội thoại / Ngữ cảnh Web thời gian thực / Câu hỏi hiện tại.
    """
    current_time_str = get_vietnam_time_str()
    system_prompt = reasoning.get_persona_prompt(persona) + (
        f"\n\n🕒 MỐC THỜI GIAN THỰC HIỆN TẠI CỦA HỆ THỐNG: {current_time_str}.\n"
        "1. CÂU ĐẦU TRỌNG TÂM: Luôn mở đầu câu trả lời bằng 1-3 câu ngắn gọn, trực diện, giải đáp ngay thắc mắc cốt lõi của người dùng. Sau đó mới đến phân tích, giải thích hoặc bảng số liệu chi tiết.\n"
        "2. Với dữ liệu nhiều ý, so sánh, thông số kỹ thuật, hoặc giá cả: Trình bày bảng Markdown rõ ràng (| Tiêu chí | Cột 1 | Cột 2 |).\n"
        "3. TUYỆT ĐỐI KHÔNG tự tạo mục 'Nguồn tham khảo' hay danh sách link ở cuối — hệ thống sẽ tự động thêm link nguồn.\n"
        "4. KẾT HỢP DỮ LIỆU INTERNET & KIẾN THỨC BÁCH KHOA THEO THỜI GIAN THỰC:\n"
        "   - Một số lĩnh vực (như CÔNG NGHỆ, MÔ HÌNH AI, PHẦN MỀM, PHẦN CỨNG) cập nhật liên tục từng ngày, từng giờ.\n"
        "   - Khi có khối 'DỮ LIỆU INTERNET THỜI GIAN THỰC', hãy ưu tiên cập nhật số liệu và sự kiện mới nhất từ khối dữ liệu này, đối chiếu với tri thức nền tảng của bạn để tổng hợp bức tranh công nghệ hoàn chỉnh và cập nhật nhất tính đến hiện tại.\n"
        "   - Nếu dữ liệu internet chưa đề cập hết hoặc còn thiếu: bạn ĐƯỢC PHÉP linh hoạt kết hợp với kiến thức nền tảng của mình để giải thích cặn kẽ, đầy đủ, nêu rõ phiên bản mới nhất bạn biết. Tuyệt đối KHÔNG trả lời cộc lốc 'không có dữ liệu'.\n"
        "   - Khi không có khối dữ liệu này, bạn tự do sử dụng toàn bộ tri thức bách khoa của mình để hỗ trợ và trò chuyện bình thường."
    )
    if profile_summary:
        system_prompt += (
            f"\n\n📋 HỒ SƠ VỀ NGƯỜI BẠN ĐANG TRÒ CHUYỆN (dùng để trả lời gần gũi/đúng ngữ cảnh hơn, "
            f"KHÔNG đọc lại nguyên văn cho họ):\n{profile_summary}"
        )
    if nickname:
        system_prompt += (
            f"\n5. Người bạn đang trò chuyện cùng muốn được gọi là '{nickname}'. "
            f"Thỉnh thoảng gọi họ bằng tên này cho gần gũi, không lạm dụng liên tục."
        )

    if not messages:
        return [{"role": "system", "content": system_prompt}]

    last_msg = messages[-1]
    history_messages = messages[:-1]
    user_query = last_msg.get("content", "")

    is_comparison = any(kw in user_query.lower() for kw in COMPARISON_TRIGGER_KEYWORDS)
    table_instruction = (
        "\n⚠️ BẮT BUỘC: đây là câu hỏi so sánh — PHẢI trình bày phần so sánh chính dưới dạng BẢNG MARKDOWN "
        "(dùng cú pháp | Cột 1 | Cột 2 |), liệt kê rõ từng tiêu chí trên từng hàng. "
        "Không viết so sánh dưới dạng đoạn văn dài."
        if is_comparison else ""
    )

    formatted_user_query = user_query
    if web_context and last_msg.get("role") == "user":
        concise_instruction = (
            "\n⚠️ ĐẶC BIỆT: Yêu cầu trả lời CỰC KỲ NGẮN GỌN (tối đa 3-4 câu), đi thẳng vào số liệu/sự việc chính."
            if force_concise else ""
        )
        clean_web = default_context_manager.trim_text_by_tokens(
            web_context,
            max_tokens=default_context_manager.max_web_budget,
            truncation_marker="\n...[Dữ liệu web đã được cắt ngắn để vừa ngữ cảnh]",
        )
        formatted_user_query = (
            f"--- DỮ LIỆU INTERNET THỜI GIAN THỰC (Ghi nhận lúc: {current_time_str}) ---\n"
            f"{clean_web}\n"
            f"--- KẾT THÚC DỮ LIỆU ---\n\n"
            f"Nhiệm vụ: Dựa vào DỮ LIỆU INTERNET ở trên và câu hỏi của bạn mình, hãy phản hồi một cách tự nhiên, hữu ích và cập nhật theo thời gian thực:\n"
            f"👉 \"{user_query}\"\n\n"
            f"QUY TẮC PHẢN HỒI THÔNG MINH & CẬP NHẬT CÔNG NGHỆ THỜI GIAN THỰC:\n"
            f"- ƯU TIÊN SỐ 1: Sử dụng số liệu, sự kiện và thông tin cập nhật từ DỮ LIỆU INTERNET ở trên.\n"
            f"- ĐỐI CHIẾU & KẾT HỢP TRI THỨC BÁCH KHOA: Với các chủ đề công nghệ cập nhật từng giờ, hãy kết hợp thông tin vừa tìm thấy với tri thức nền tảng của bạn để phân tích tính năng, sự nâng cấp và phiên bản mới nhất tính đến thời điểm hiện tại ({current_time_str}).\n"
            f"- Nếu DỮ LIỆU INTERNET chỉ có thông tin vắn tắt (nhặt từ từ khóa cốt lõi): Hãy chủ động dùng kiến thức nền tảng giải thích bản chất công nghệ, làm rõ các điểm cốt lõi cho bạn mình. TUYỆT ĐỐI TRÁNH trả lời cụt ngủn là 'không có dữ liệu'.\n"
            f"- Nếu lịch sử trò chuyện trước đó có thông tin khác với DỮ LIỆU INTERNET, ưu tiên số liệu mới trong DỮ LIỆU INTERNET.\n"
            f"- Trình bày gãy gọn (dùng gạch đầu dòng, bảng nếu cần) nhưng vẫn giữ văn phong thân thiện, tự nhiên.\n"
            f"- Danh sách link tham khảo sẽ được thêm tự động vào cuối tin nhắn.\n"
            f"{concise_instruction}"
            f"{table_instruction}\n"
        )
    elif is_comparison and last_msg.get("role") == "user":
        formatted_user_query = f"{user_query}\n{table_instruction}"

    formatted, stats = default_context_manager.allocate_and_build(
        system_prompt=system_prompt,
        history_messages=history_messages,
        web_context="",
        user_query_override=formatted_user_query if last_msg.get("role") == "user" else None,
    )

    logger.info(
        "📊 Context Budget: total_in=%d (sys=%d, web=%d, hist=%d, user=%d), remain=%d/%d, hist_truncated=%d",
        stats["total_input_tokens"],
        stats["system_tokens"],
        stats["web_tokens"],
        stats["history_tokens"],
        stats["user_tokens"],
        stats["estimated_remaining"],
        stats["total_budget"],
        stats["was_history_truncated"],
    )

    return formatted


# ── LLM calls ─────────────────────────────────────────────────────────────────
def _gen_options(has_web: bool) -> dict:
    return (
        {"temperature": 0.15, "top_p": 0.8, "num_ctx": OLLAMA_CONTEXT_SIZE}
        if has_web else
        {"temperature": 0.6,  "top_p": 0.9, "num_ctx": OLLAMA_CONTEXT_SIZE}
    )


async def chat_with_llm(
    messages: list[dict], model: str, web_context: str = "", force_concise: bool = False,
    nickname: Optional[str] = None, persona: Optional[str] = None, profile_summary: str = "",
) -> str:
    """Gọi Ollama và thu thập toàn bộ câu trả lời 1 lần.
    Sử dụng stream ngầm để giữ kết nối socket luôn nhận dữ liệu liên tục,
    tránh hoàn toàn việc bị httpx timeout khi suy luận dài hoặc prompt lớn."""
    last_err: Optional[Exception] = None
    for attempt in range(1, OLLAMA_RETRY_ATTEMPTS + 1):
        collected = []
        is_error = False
        try:
            async for piece in chat_with_llm_stream(
                messages, model, web_context, force_concise, nickname, persona, profile_summary
            ):
                if piece.startswith("❌ Lỗi Ollama (stream):"):
                    is_error = True
                    last_err = piece
                    break
                collected.append(piece)
            if not is_error and collected:
                return "".join(collected).strip()
        except Exception as e:
            last_err = e
            logger.warning(f"⚠️ Lỗi gọi Ollama (lần {attempt}/{OLLAMA_RETRY_ATTEMPTS}): {e}")
        if attempt < OLLAMA_RETRY_ATTEMPTS:
            await asyncio.sleep(1.0)

    return (
        f"❌ Không kết nối được tới Ollama sau {OLLAMA_RETRY_ATTEMPTS} lần thử ({last_err}).\n"
        f"💡 Kiểm tra Ollama đã chạy chưa (`ollama serve`) và model `{model}` đã được `ollama pull` chưa."
    )


async def chat_with_llm_stream(
    messages: list[dict], model: str, web_context: str = "", force_concise: bool = False,
    nickname: Optional[str] = None, persona: Optional[str] = None, profile_summary: str = "",
):
    """Async generator: yield từng đoạn text nhận được từ Ollama (stream=True, NDJSON)."""
    formatted = build_grounded_messages(messages, web_context, force_concise, nickname, persona, profile_summary)
    try:
        async with _http_client.stream(
            "POST", f"{OLLAMA_BASE_URL}/api/chat",
            json={"model": model, "messages": formatted, "stream": True,
                  "options": _gen_options(bool(web_context))},
            timeout=OLLAMA_TIMEOUT_SEC,
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.strip():
                    continue
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue
                piece = chunk.get("message", {}).get("content", "")
                if piece:
                    yield piece
                if chunk.get("done"):
                    break
    except Exception as e:
        yield (
            f"❌ Lỗi Ollama (stream): {e}\n"
            f"💡 Kiểm tra Ollama đã chạy chưa (`ollama serve`) và model `{model}` đã được `ollama pull` chưa."
        )