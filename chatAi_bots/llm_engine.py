"""
llm_engine.py — Giao tiếp với Ollama: model cache, build grounded messages,
                chat_with_llm (non-stream) và chat_with_llm_stream (async generator).
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Optional

import reasoning
from bot_logger import logger
from config import (
    OLLAMA_BASE_URL, OLLAMA_TIMEOUT_SEC, OLLAMA_RETRY_ATTEMPTS,
    COMPARISON_TRIGGER_KEYWORDS,
)

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


# ── Grounded message builder ───────────────────────────────────────────────────
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
    system_prompt = reasoning.get_persona_prompt(persona) + (
        "\n2. Với dữ liệu nhiều ý, số liệu, hoặc so sánh: dùng Bảng hoặc gạch đầu dòng cho dễ đọc.\n"
        "3. Danh sách link đầy đủ sẽ được hệ thống tự động thêm vào cuối câu trả lời.\n"
        "4. QUAN TRỌNG: Khi tin nhắn có kèm khối 'DỮ LIỆU INTERNET THỜI GIAN THỰC', vai trò của bạn CHỈ LÀ "
        "TỔNG HỢP lại thông tin đó, TUYỆT ĐỐI KHÔNG được dùng kiến thức đã học sẵn (nội tại) của bạn để trả lời "
        "hay bổ sung — kiến thức đó có thể đã lỗi thời. Nếu không có khối dữ liệu này, bạn mới được dùng kiến "
        "thức chung của mình để trò chuyện bình thường."
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

    formatted = [{"role": "system", "content": system_prompt}]
    formatted.extend(messages[:-1])

    last_msg = messages[-1]
    user_query = last_msg.get("content", "")

    is_comparison = any(kw in user_query.lower() for kw in COMPARISON_TRIGGER_KEYWORDS)
    table_instruction = (
        "\n⚠️ BẮT BUỘC: đây là câu hỏi so sánh — PHẢI trình bày phần so sánh chính dưới dạng BẢNG MARKDOWN "
        "(dùng cú pháp | Cột 1 | Cột 2 |), liệt kê rõ từng tiêu chí trên từng hàng. "
        "Không viết so sánh dưới dạng đoạn văn dài."
        if is_comparison else ""
    )

    if web_context and last_msg.get("role") == "user":
        concise_instruction = (
            "\n⚠️ ĐẶC BIỆT: Yêu cầu trả lời CỰC KỲ NGẮN GỌN (tối đa 3-4 câu), đi thẳng vào số liệu/sự việc chính."
            if force_concise else ""
        )
        grounded_user_content = (
            f"--- DỮ LIỆU INTERNET THỜI GIAN THỰC ---\n"
            f"{web_context}\n"
            f"--- KẾT THÚC DỮ LIỆU ---\n\n"
            f"Nhiệm vụ: Dựa vào DỮ LIỆU INTERNET ở trên, trả lời câu hỏi sau của bạn mình một cách tự nhiên:\n"
            f"👉 \"{user_query}\"\n\n"
            f"QUY TẮC RAG BẮT BUỘC (ƯU TIÊN CAO NHẤT — GHI ĐÈ MỌI KIẾN THỨC NỘI TẠI CỦA BẠN):\n"
            f"- Vai trò của bạn lúc này CHỈ LÀ TỔNG HỢP (summarizer). TUYỆT ĐỐI KHÔNG dùng kiến thức có sẵn của bạn.\n"
            f"- Chỉ dùng thông tin có trong DỮ LIỆU INTERNET ở trên, không tự suy diễn, không bịa thêm số liệu.\n"
            f"- Nếu DỮ LIỆU INTERNET không đủ, hãy nói thẳng là chưa tìm thấy đủ thông tin.\n"
            f"- Nếu lịch sử trò chuyện trước đó có thông tin khác với DỮ LIỆU INTERNET, dùng DỮ LIỆU INTERNET.\n"
            f"- Dùng gạch đầu dòng, bảng so sánh nếu cần, nhưng vẫn giữ văn phong tự nhiên.\n"
            f"- Danh sách link đầy đủ sẽ được thêm tự động vào cuối tin nhắn.\n"
            f"{concise_instruction}"
            f"{table_instruction}\n"
        )
        formatted.append({"role": "user", "content": grounded_user_content})
    elif is_comparison and last_msg.get("role") == "user":
        formatted.append({"role": "user", "content": f"{user_query}\n{table_instruction}"})
    else:
        formatted.append(last_msg)

    return formatted


# ── LLM calls ─────────────────────────────────────────────────────────────────
def _gen_options(has_web: bool) -> dict:
    return (
        {"temperature": 0.15, "top_p": 0.8, "num_ctx": 4096}
        if has_web else
        {"temperature": 0.6,  "top_p": 0.9, "num_ctx": 4096}
    )


async def chat_with_llm(
    messages: list[dict], model: str, web_context: str = "", force_concise: bool = False,
    nickname: Optional[str] = None, persona: Optional[str] = None, profile_summary: str = "",
) -> str:
    """Gọi Ollama /api/chat KHÔNG streaming — trả về toàn bộ câu trả lời 1 lần."""
    formatted = build_grounded_messages(messages, web_context, force_concise, nickname, persona, profile_summary)
    last_err: Optional[Exception] = None
    for attempt in range(1, OLLAMA_RETRY_ATTEMPTS + 1):
        try:
            r = await _http_client.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json={"model": model, "messages": formatted, "stream": False,
                      "options": _gen_options(bool(web_context))},
                timeout=OLLAMA_TIMEOUT_SEC,
            )
            r.raise_for_status()
            return r.json()["message"]["content"].strip()
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
