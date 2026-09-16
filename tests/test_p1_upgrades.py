"""
tests/test_p1_upgrades.py — Bộ kiểm thử tự động cho Giai đoạn 1 (P1):
1. Hệ thống Plugin & Modular Skills (BaseSkill, SkillRegistry, Auto-discovery, Plug & Play)
2. Bộ quản lý Ngân sách Token & Cửa sổ Ngữ cảnh (Token Estimator, Sliding Window Budget, LLM Integration)
"""

import asyncio
import unittest
from typing import Optional

import httpx

from skills.base import BaseSkill, SkillResult
from skills.registry import SkillRegistry, default_registry
from skills.weather import WeatherSkill, skill_weather
from skills.news import NewsSkill, skill_news
from core.context_manager import (
    estimate_tokens, estimate_messages_tokens, ContextBudgetManager, default_context_manager
)
from core.llm_engine import build_grounded_messages


class TestModularSkillsSystem(unittest.TestCase):
    """Kiểm thử tính mô-đun và khả năng thêm/bớt dễ dàng của hệ thống Skills."""

    def setUp(self):
        self.registry = SkillRegistry()

    def test_custom_plugin_plug_and_play(self):
        """Thử nghiệm tạo một Skill mới (ví dụ CryptoSkill) và cắm vào hệ thống (Plug & Play)."""
        class CryptoSkill(BaseSkill):
            name = "crypto"
            display_name = "Giá Tiền Mã Hoá"
            description = "Tra cứu giá Bitcoin, Ethereum và các đồng tiền mã hoá theo thời gian thực."
            command = "crypto"
            parameters_schema = {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Mã coin: BTC, ETH, SOL..."},
                },
                "required": ["symbol"],
            }

            async def execute(self, symbol: str = "BTC", **kwargs) -> SkillResult:
                sym = symbol.upper().strip()
                mock_prices = {"BTC": "95,000 USD", "ETH": "3,200 USD"}
                price = mock_prices.get(sym, "100 USD")
                return SkillResult(
                    success=True,
                    text=f"🪙 Giá *{sym}*: *{price}*",
                    data={"symbol": sym, "price": price},
                )

        # 1. Đăng ký skill mới vào registry
        crypto_skill = CryptoSkill()
        self.registry.register(crypto_skill)

        # 2. Kiểm tra truy xuất theo tên và theo lệnh telegram
        self.assertIsNotNone(self.registry.get("crypto"))
        self.assertIsNotNone(self.registry.get_by_command("crypto"))
        self.assertEqual(self.registry.get_by_command("/crypto"), crypto_skill)

        # 3. Kiểm tra thực thi skill
        loop = asyncio.new_event_loop()
        try:
            res = loop.run_until_complete(crypto_skill.execute(symbol="BTC"))
            self.assertTrue(res.success)
            self.assertIn("95,000 USD", res.text)
        finally:
            loop.close()

        # 4. Kiểm tra xuất schema cho Ollama Tool Calling
        tools = self.registry.get_ollama_tools()
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0]["function"]["name"], "crypto")
        self.assertIn("symbol", tools[0]["function"]["parameters"]["properties"])

        # 5. Thử nghiệm BẬT/TẮT tính năng (Bớt skill dễ dàng)
        crypto_skill.enabled = False
        self.assertIsNone(self.registry.get("crypto"))
        self.assertIsNone(self.registry.get_by_command("crypto"))
        self.assertEqual(len(self.registry.get_ollama_tools()), 0)

        # 6. Thử nghiệm gỡ bỏ hoàn toàn (Unregister)
        crypto_skill.enabled = True
        removed = self.registry.unregister("crypto")
        self.assertEqual(removed, crypto_skill)
        self.assertIsNone(self.registry.get("crypto"))

    def test_default_registry_has_core_skills(self):
        """Kiểm tra default_registry đã tự động phát hiện weather và news."""
        weather = default_registry.get("weather")
        news = default_registry.get("news")

        self.assertIsNotNone(weather)
        self.assertIsNotNone(news)
        self.assertEqual(default_registry.get_by_command("weather"), weather)
        self.assertEqual(default_registry.get_by_command("news"), news)

    def test_http_client_injection(self):
        """Kiểm tra phân phối http_client tập trung tới tất cả các skills."""
        client = httpx.AsyncClient()
        self.registry.register(WeatherSkill())
        self.registry.set_http_client(client)

        w = self.registry.get("weather")
        self.assertEqual(w.http_client, client)

        # Thử đăng ký thêm skill sau khi đã set_http_client
        n = NewsSkill()
        self.registry.register(n)
        self.assertEqual(n.http_client, client)


class TestTokenBudgetAndContext(unittest.TestCase):
    """Kiểm thử thuật toán ước lượng Token và Context Window Manager."""

    def test_token_estimator(self):
        """Đo độ chính xác của hàm ước lượng token trên tiếng Việt, tiếng Anh và code."""
        text_vi = "Thời tiết tại thành phố Hà Nội hôm nay rất đẹp và trong lành."
        tokens_vi = estimate_tokens(text_vi)
        # 14 từ tiếng Việt có dấu -> dự kiến khoảng 15 - 25 tokens
        self.assertTrue(14 <= tokens_vi <= 28, f"Unexpected token count: {tokens_vi}")

        text_en = "Artificial Intelligence is transforming software development."
        tokens_en = estimate_tokens(text_en)
        # 7 từ tiếng Anh -> dự kiến khoảng 8 - 14 tokens
        self.assertTrue(7 <= tokens_en <= 16, f"Unexpected token count: {tokens_en}")

        empty_tokens = estimate_tokens("")
        self.assertEqual(empty_tokens, 0)

    def test_sliding_window_token_budget(self):
        """Kiểm tra cắt tỉa lịch sử khi vượt quá ngân sách."""
        manager = ContextBudgetManager(
            total_budget=2000,
            generation_reserve=500,
            max_system_budget=300,
            max_web_budget=400,
        )

        sys_prompt = "You are a helpful assistant."
        # Tạo 50 tin nhắn, mỗi tin ~ 30 tokens = ~1500 tokens (vượt quá ngân sách history còn lại)
        history = [
            {
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"Tin nhắn hội thoại thứ {i}: nội dung thảo luận chi tiết về kỹ thuật lập trình hệ thống.",
            }
            for i in range(50)
        ]

        messages, stats = manager.allocate_and_build(
            system_prompt=sys_prompt,
            history_messages=history,
            web_context="Dữ liệu tìm kiếm web ngắn gọn.",
            user_query_override="Câu hỏi cuối cùng của người dùng.",
        )

        # Tổng input tokens phải nhỏ hơn hoặc bằng (total_budget - generation_reserve)
        max_allowed_input = manager.total_budget - manager.generation_reserve
        self.assertLessEqual(stats["total_input_tokens"], max_allowed_input + 50)
        self.assertEqual(stats["was_history_truncated"], 1)

        # Phải bảo đảm có thông báo cắt tỉa cho LLM
        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("[Các tin nhắn trước đó đã được tự động lược bớt", messages[1]["content"])

        # Tin nhắn cuối cùng phải là câu hỏi người dùng
        self.assertEqual(messages[-1]["role"], "user")
        self.assertEqual(messages[-1]["content"], "Câu hỏi cuối cùng của người dùng.")

    def test_web_context_truncation(self):
        """Kiểm tra cắt tỉa ngữ cảnh web search khi dữ liệu quá dài."""
        manager = ContextBudgetManager(max_web_budget=100)
        long_web = "Đây là dòng thông tin web số 1.\n" * 200
        trimmed = manager.trim_text_by_tokens(long_web, max_tokens=100)

        self.assertLessEqual(estimate_tokens(trimmed), 130)
        self.assertTrue(trimmed.endswith("...[Dữ liệu đã được cắt gọn]"))

    def test_build_grounded_messages_integration(self):
        """Kiểm tra tích hợp end-to-end trong llm_engine.build_grounded_messages."""
        history = [
            {"role": "user", "content": f"Turn {i}: xin chào bot"}
            for i in range(40)
        ]
        history.append({"role": "user", "content": "So sánh Python và Rust"})

        payload = build_grounded_messages(
            messages=history,
            web_context="Python dễ học, Rust an toàn bộ nhớ.",
            nickname="Alex",
            persona="chuyen_gia",
            profile_summary="Người dùng thích lập trình backend.",
        )

        self.assertTrue(len(payload) > 2)
        self.assertEqual(payload[0]["role"], "system")
        # System prompt phải chứa persona và hồ sơ
        self.assertIn("Alex", payload[0]["content"])
        self.assertIn("Người dùng thích lập trình backend", payload[0]["content"])
        # Câu hỏi so sánh phải kèm bảng markdown
        self.assertIn("BẢNG MARKDOWN", payload[-1]["content"])


if __name__ == "__main__":
    unittest.main()
