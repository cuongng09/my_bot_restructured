"""
reasoning.py — Nâng cấp "tư duy trả lời" cho my_bot.py
Hoàn toàn local (chỉ gọi Ollama đang chạy sẵn), KHÔNG cần API ngoài.

Bao gồm:
  1. classify_complexity()   — phân loại câu hỏi: simple / medium / complex
  2. wrap_with_hidden_reasoning() / extract_final_answer() — ép model "nghĩ" trong
     khối ẩn <suy_nghi>...</suy_nghi> trước khi đưa câu trả lời thật trong <tra_loi>...</tra_loi>,
     chỉ áp dụng cho câu hỏi complex để không tốn thời gian/token cho chat phiếm.
  3. ThinkingStreamFilter — bộ lọc dùng khi STREAMING, để không hiển thị phần
     <suy_nghi> ra màn hình cho user (chỉ hiện phần <tra_loi>).
  4. PERSONAS — vài preset tính cách, người dùng chọn qua lệnh /persona.
  5. summarize_for_long_term_memory() — nén lịch sử cũ thành 1 đoạn "hồ sơ" ngắn,
     dùng LLM nội bộ (Ollama) để tóm tắt, không cần thêm dịch vụ nào.

Cách tích hợp: xem UPGRADE_GUIDE.md
"""

import re
from typing import Optional

# ═══════════════════════════════════════════════════════════════
# 1. PHÂN LOẠI ĐỘ PHỨC TẠP CÂU HỎI
# ═══════════════════════════════════════════════════════════════
_COMPLEX_KEYWORDS = [
    "phân tích", "so sánh", "giải thích chi tiết", "tại sao", "vì sao", "làm sao để",
    "thiết kế", "viết code", "viết chương trình", "lập kế hoạch", "chiến lược",
    "ưu nhược điểm", "đánh giá", "tư vấn", "nên chọn", "chứng minh", "suy luận",
    "tính toán", "giải bài", "debug", "sửa lỗi", "tối ưu",
]
_SIMPLE_KEYWORDS = [
    "chào", "hi", "hello", "ok", "cảm ơn", "cám ơn", "thanks", "ừ", "ừm", "vâng",
    "bye", "tạm biệt", "hihi", "haha",
]


def classify_complexity(text: str) -> str:
    """Trả về 'simple' | 'medium' | 'complex' dựa trên từ khóa + độ dài + số câu hỏi.
    Dùng để quyết định: có cần suy luận ẩn không, trả lời dài/ngắn bao nhiêu (kể cả cho Voice)."""
    low = text.lower().strip()
    word_count = len(low.split())
    question_marks = low.count("?")

    if word_count <= 6 and any(kw in low for kw in _SIMPLE_KEYWORDS):
        return "simple"

    if any(kw in low for kw in _COMPLEX_KEYWORDS):
        return "complex"
    if question_marks >= 2 or word_count >= 40:
        return "complex"

    if word_count <= 8 and question_marks <= 1:
        return "simple"

    return "medium"


# ═══════════════════════════════════════════════════════════════
# 2. SUY LUẬN ẨN (hidden chain-of-thought)
# ═══════════════════════════════════════════════════════════════
_THINK_OPEN, _THINK_CLOSE = "<suy_nghi>", "</suy_nghi>"
_ANSWER_OPEN, _ANSWER_CLOSE = "<tra_loi>", "</tra_loi>"

_HIDDEN_REASONING_INSTRUCTION = (
    "\n\n⚠️ YÊU CẦU BẮT BUỘC VỀ ĐỊNH DẠNG (câu hỏi này khá phức tạp, cần suy nghĩ kỹ trước khi trả lời):\n"
    f"1. Đầu tiên, viết phần suy luận từng bước (ngắn gọn, không lan man) bên trong {_THINK_OPEN}...{_THINK_CLOSE}. "
    "Đây là phần NHÁP, người dùng sẽ KHÔNG nhìn thấy — cứ thoải mái phân tích, liệt kê giả định, kiểm tra logic.\n"
    f"2. Sau đó, viết câu trả lời CUỐI CÙNG, hoàn chỉnh, tự nhiên (đúng phong cách trò chuyện đã quy định) "
    f"bên trong {_ANSWER_OPEN}...{_ANSWER_CLOSE}. Đây là phần DUY NHẤT người dùng sẽ đọc.\n"
    f"3. Không viết gì bên ngoài 2 khối trên."
)


def wrap_with_hidden_reasoning(user_content: str) -> str:
    """Thêm hướng dẫn suy luận ẩn vào cuối nội dung user_content (chỉ gọi khi complexity == 'complex')."""
    return user_content + _HIDDEN_REASONING_INSTRUCTION


_answer_re = re.compile(re.escape(_ANSWER_OPEN) + r"(.*?)" + re.escape(_ANSWER_CLOSE), re.DOTALL)
_think_re = re.compile(re.escape(_THINK_OPEN) + r".*?" + re.escape(_THINK_CLOSE), re.DOTALL)


def extract_final_answer(raw_text: str) -> str:
    """Bóc phần <tra_loi>...</tra_loi>. Nếu model không tuân theo định dạng (vẫn hay xảy ra với
    model nhỏ), fallback: xóa hết khối <suy_nghi> rồi trả về phần còn lại — không bao giờ để
    lộ phần nháp ra cho user, và không bao giờ trả về rỗng nếu raw_text có nội dung."""
    m = _answer_re.search(raw_text)
    if m:
        return m.group(1).strip()
    # Fallback: loại bỏ khối suy nghĩ (nếu có) và các tag lẻ còn sót
    cleaned = _think_re.sub("", raw_text)
    cleaned = cleaned.replace(_THINK_OPEN, "").replace(_THINK_CLOSE, "")
    cleaned = cleaned.replace(_ANSWER_OPEN, "").replace(_ANSWER_CLOSE, "")
    return cleaned.strip() or raw_text.strip()


class ThinkingStreamFilter:
    """Bộ lọc stateful dùng khi STREAMING từng mẩu text từ Ollama.
    Nuốt (không yield) mọi thứ bên trong <suy_nghi>...</suy_nghi>, chỉ yield phần bên trong
    <tra_loi>...</tra_loi> (hoặc toàn bộ nếu model không theo định dạng — an toàn, không mất câu trả lời).

    Cách dùng:
        f = ThinkingStreamFilter()
        async for piece in chat_with_llm_stream(...):
            visible = f.feed(piece)
            if visible:
                yield visible
        yield f.flush()   # phòng trường hợp model không đóng tag đúng cách
    """

    def __init__(self):
        self._buf = ""
        self._state = "before_or_plain"  # before_or_plain -> in_think -> after_think -> in_answer -> done
        self._saw_any_tag = False

    @staticmethod
    def _find_any(buf: str, tags: list[str]):
        """Tìm tag xuất hiện sớm nhất trong buf. Trả về (index, tag) hoặc (-1, None)."""
        best_idx, best_tag = -1, None
        for t in tags:
            i = buf.find(t)
            if i != -1 and (best_idx == -1 or i < best_idx):
                best_idx, best_tag = i, t
        return best_idx, best_tag

    def feed(self, piece: str) -> str:
        self._buf += piece
        out = ""

        while True:
            if self._state == "before_or_plain":
                idx, tag = self._find_any(self._buf, [_THINK_OPEN, _ANSWER_OPEN])
                if tag is not None:
                    self._saw_any_tag = True
                    pre = self._buf[:idx]
                    out += pre  # text trước tag (hiếm khi có, nhưng cứ hiện ra cho an toàn)
                    self._buf = self._buf[idx + len(tag):]
                    self._state = "in_think" if tag == _THINK_OPEN else "in_answer"
                    continue
                # Chưa thấy tag nào — có thể model KHÔNG dùng định dạng suy luận ẩn (câu hỏi đơn giản).
                # Giữ lại vài ký tự cuối phòng khi tag bị cắt giữa chừng qua nhiều piece (KHÔNG được
                # xóa mất — chỉ trì hoãn hiển thị tới piece sau).
                keep = max(len(_THINK_OPEN), len(_ANSWER_OPEN)) - 1
                if len(self._buf) > keep:
                    out += self._buf[:-keep] if keep else self._buf
                    self._buf = self._buf[-keep:] if keep else ""
                break

            elif self._state == "in_think":
                idx = self._buf.find(_THINK_CLOSE)
                if idx != -1:
                    self._buf = self._buf[idx + len(_THINK_CLOSE):]
                    self._state = "after_think"
                    continue
                # Nuốt phần suy luận, nhưng GIỮ lại đuôi buffer đề phòng </suy_nghi> bị cắt giữa 2 piece
                keep = len(_THINK_CLOSE) - 1
                self._buf = self._buf[-keep:] if keep and len(self._buf) > keep else self._buf
                break

            elif self._state == "after_think":
                idx = self._buf.find(_ANSWER_OPEN)
                if idx != -1:
                    self._buf = self._buf[idx + len(_ANSWER_OPEN):]
                    self._state = "in_answer"
                    continue
                keep = len(_ANSWER_OPEN) - 1
                self._buf = self._buf[-keep:] if keep and len(self._buf) > keep else self._buf
                break

            elif self._state == "in_answer":
                idx = self._buf.find(_ANSWER_CLOSE)
                if idx != -1:
                    out += self._buf[:idx]
                    self._buf = self._buf[idx + len(_ANSWER_CLOSE):]
                    self._state = "done"
                    continue
                # Giữ lại đuôi phòng </tra_loi> bị cắt giữa 2 piece, phần còn lại xuất ra ngay (streaming)
                keep = len(_ANSWER_CLOSE) - 1
                if len(self._buf) > keep:
                    out += self._buf[:-keep] if keep else self._buf
                    self._buf = self._buf[-keep:] if keep else ""
                break

            else:  # done — model vẫn còn sinh thêm thì bỏ qua
                self._buf = ""
                break

        return out

    def flush(self) -> str:
        """Gọi khi stream kết thúc — trả nốt phần còn kẹt trong buffer nếu model chưa từng thấy
        tag nào (nghĩa là chat bình thường không theo định dạng suy luận ẩn) hoặc quên đóng tag."""
        remainder = self._buf
        self._buf = ""
        if self._state in ("before_or_plain",) and not self._saw_any_tag:
            return remainder
        if self._state == "in_answer":
            return remainder
        return ""


# ═══════════════════════════════════════════════════════════════
# 3. PERSONA (tính cách / giọng văn)
# ═══════════════════════════════════════════════════════════════
PERSONAS: dict[str, dict[str, str]] = {
    "ban_than": {
        "label": "🧑‍🤝‍🧑 Bạn thân",
        "prompt": (
            "Bạn là một người bạn đồng hành AI thông minh, nói chuyện tự nhiên như một người bạn thân đang "
            "trò chuyện qua Telegram — không phải một cỗ máy trả lời khô khan. Xưng 'mình', gọi người dùng là 'bạn'. "
            "Gần gũi, thoải mái, đôi khi dùng emoji cho sinh động, nhưng vẫn đi thẳng vào trọng tâm."
        ),
    },
    "chuyen_gia": {
        "label": "🎓 Chuyên gia",
        "prompt": (
            "Bạn là một trợ lý AI chuyên nghiệp, trả lời với văn phong chuẩn mực, súc tích, có cấu trúc rõ ràng "
            "(dùng gạch đầu dòng/bảng khi cần). Xưng 'tôi', gọi người dùng là 'bạn/anh/chị' tùy ngữ cảnh. "
            "Ưu tiên độ chính xác và tính logic hơn là sự thân mật."
        ),
    },
    "hai_huoc": {
        "label": "😄 Dí dỏm",
        "prompt": (
            "Bạn là một trợ lý AI hài hước, thông minh, thích chêm chút dí dỏm/châm biếm nhẹ nhàng vào câu trả lời "
            "nhưng KHÔNG bao giờ hy sinh độ chính xác để đùa cợt. Xưng 'mình', gọi người dùng là 'bạn'."
        ),
    },
    "co_van": {
        "label": "🧭 Cố vấn",
        "prompt": (
            "Bạn là một cố vấn/mentor AI điềm tĩnh, chu đáo. Khi trả lời, thường đưa thêm góc nhìn hoặc câu hỏi gợi mở "
            "giúp người dùng tự suy nghĩ sâu hơn, thay vì chỉ đưa đáp án một chiều. Xưng 'mình', gọi người dùng là 'bạn'."
        ),
    },
}
DEFAULT_PERSONA = "ban_than"


def get_persona_prompt(persona_key: Optional[str]) -> str:
    return PERSONAS.get(persona_key or DEFAULT_PERSONA, PERSONAS[DEFAULT_PERSONA])["prompt"]


# ═══════════════════════════════════════════════════════════════
# 4. TRÍ NHỚ DÀI HẠN (tóm tắt hồ sơ người dùng bằng chính Ollama)
# ═══════════════════════════════════════════════════════════════
_SUMMARY_SYSTEM_PROMPT = (
    "Bạn là bộ máy tóm tắt hồ sơ người dùng. Dựa trên đoạn hội thoại được cung cấp và hồ sơ cũ (nếu có), "
    "hãy viết lại một đoạn HỒ SƠ NGẮN GỌN (tối đa 5-6 gạch đầu dòng) về người dùng: sở thích, thói quen, "
    "công việc/lĩnh vực quan tâm, cách xưng hô họ thích, các chủ đề họ hay hỏi, thông tin cá nhân họ tự tiết lộ. "
    "CHỈ ghi thông tin có căn cứ rõ ràng trong hội thoại, KHÔNG suy đoán/bịa. "
    "Nếu hồ sơ cũ có mục nào không còn xuất hiện/không còn đúng, có thể loại bỏ. "
    "Chỉ trả về nội dung hồ sơ (gạch đầu dòng), không thêm lời dẫn."
)


async def summarize_for_long_term_memory(
    chat_with_llm_fn, model: str, recent_messages: list[dict], old_summary: Optional[str] = None,
) -> str:
    """Gọi LLM (Ollama, local) để nén lịch sử gần đây + hồ sơ cũ thành hồ sơ mới, ngắn gọn.
    `chat_with_llm_fn` = truyền vào hàm chat_with_llm() sẵn có trong my_bot.py để tái dùng logic
    gọi Ollama (retry, timeout...) mà không cần import vòng (circular import)."""
    convo_text = "\n".join(
        f"{'Người dùng' if m['role'] == 'user' else 'Trợ lý'}: {m['content']}" for m in recent_messages
    )
    old = f"\n\nHỒ SƠ CŨ:\n{old_summary}" if old_summary else ""
    prompt = f"ĐOẠN HỘI THOẠI GẦN ĐÂY:\n{convo_text}{old}\n\nHãy viết HỒ SƠ MỚI:"

    messages = [
        {"role": "system", "content": _SUMMARY_SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    # Dùng chat_with_llm gốc nhưng KHÔNG qua _build_grounded_messages (ta tự set system riêng) —
    # nên ở đây ta gọi thẳng endpoint qua callback đã bọc sẵn bên my_bot.py, xem UPGRADE_GUIDE.md.
    result = await chat_with_llm_fn(messages, model)
    return result.strip()
