# skills/crypto.py
from skills.base import BaseSkill, SkillResult

class CryptoSkill(BaseSkill):
    name = "crypto"
    display_name = "Giá Tiền Mã Hoá"
    description = "Tra cứu giá thời gian thực của các đồng tiền mã hoá (BTC, ETH, SOL, BNB...)"
    command = "crypto"  # <-- Bot sẽ tự động tạo lệnh /crypto trên Telegram!

    # Khai báo schema để LLM Ollama tự biết cách gọi hàm (Function Calling)
    parameters_schema = {
        "type": "object",
        "properties": {
            "symbol": {
                "type": "string",
                "description": "Mã đồng coin viết hoa, ví dụ: BTC, ETH, SOL, BNB, DOGE.",
                "default": "BTC"
            }
        },
        "required": ["symbol"]
    }

    async def execute(self, symbol: str = "BTC", **kwargs) -> SkillResult:
        # Lấy tham số: từ lệnh /crypto <sym> hoặc từ LLM tool calling
        sym = (symbol or kwargs.get("query") or "BTC").upper().strip()
        pair = f"{sym}USDT"

        try:
            # self.http_client đã được hệ thống tự động inject sẵn!
            resp = await self.http_client.get(
                f"https://api.binance.com/api/v3/ticker/price",
                params={"symbol": pair},
                timeout=5
            )
            data = resp.json()
            if "price" not in data:
                return SkillResult(success=False, text=f"❓ Không tìm thấy mã coin: *{sym}*")

            price = float(data["price"])
            formatted_price = f"{price:,.2f}" if price >= 1 else f"{price:.6f}"

            msg = (
                f"🪙 *Giá {sym} (Binance)*\n\n"
                f"💵 Giá hiện tại: *${formatted_price} USDT*"
            )
            return SkillResult(success=True, text=msg, data=data)

        except Exception as e:
            return SkillResult(success=False, text=f"❌ Lỗi tra cứu giá {sym}: {e}")