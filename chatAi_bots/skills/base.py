"""
skills/base.py — Lớp cơ sở (Base Class) và cấu trúc dữ liệu cho hệ thống Skills dạng Mô-đun (Plugins).
Thiết kế theo nguyên tắc Plug & Play: mỗi skill là 1 module độc lập, có thể thêm/bớt dễ dàng.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx


@dataclass
class SkillResult:
    """Kết quả trả về chuẩn hóa từ bất kỳ Skill nào."""
    success: bool
    text: str = ""
    data: Any = None
    file_path: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def __str__(self) -> str:
        return self.text


class BaseSkill(ABC):
    """
    Lớp cơ sở trừu tượng cho mọi Skill / Plugin trong hệ thống.
    
    Khi thêm một kỹ năng mới:
    1. Tạo 1 file trong thư mục skills/ kế thừa BaseSkill.
    2. Điền đầy đủ name, description, parameters_schema, command (nếu có).
    3. Cài đặt phương thức execute().
    Hệ thống SkillRegistry sẽ tự động phát hiện và nạp kỹ năng mà không cần sửa Core.
    """
    name: str = ""
    display_name: str = ""
    description: str = ""
    command: Optional[str] = None          # Lệnh Telegram tương ứng, vd 'weather' -> /weather
    enabled: bool = True                   # Bật/tắt nhanh mà không cần xóa code
    parameters_schema: Optional[dict] = None  # JSON schema cho Ollama / OpenAI Tool Calling

    def __init__(self, http_client: Optional[httpx.AsyncClient] = None):
        self._http_client = http_client
        self._fallback_client: Optional[httpx.AsyncClient] = None

    @property
    def http_client(self) -> httpx.AsyncClient:
        """Trả về HTTP client dùng chung, hoặc tự động tạo fallback client nếu chưa được inject."""
        if self._http_client is not None and not self._http_client.is_closed:
            return self._http_client
        if self._fallback_client is None or self._fallback_client.is_closed:
            self._fallback_client = httpx.AsyncClient(follow_redirects=True)
        return self._fallback_client

    @http_client.setter
    def http_client(self, client: Optional[httpx.AsyncClient]) -> None:
        self._http_client = client

    def set_http_client(self, client: httpx.AsyncClient) -> None:
        """Inject HTTP client dùng chung để tối ưu connection pooling."""
        self._http_client = client

    @abstractmethod
    async def execute(self, **kwargs) -> SkillResult:
        """Thực thi logic chính của kỹ năng.
        
        Args:
            **kwargs: Các tham số được truyền từ lệnh Telegram hoặc LLM Tool Calling.
        Returns:
            SkillResult chứa văn bản phản hồi và dữ liệu đính kèm nếu có.
        """
        pass

    async def can_handle(self, query: str) -> bool:
        """Dùng cho rule-based matching hoặc regex nhanh nếu không dùng LLM Tool Calling."""
        return False

    def to_ollama_tool(self) -> dict:
        """Chuyển đổi metadata của skill sang định dạng Function Calling chuẩn của Ollama / OpenAI."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description or self.display_name or self.name,
                "parameters": self.parameters_schema or {
                    "type": "object",
                    "properties": {},
                },
            },
        }
