"""
skills/weather.py — Plugin Thời tiết + chất lượng không khí (open-meteo, không cần API key).
Triển khai dạng BaseSkill theo kiến trúc mô-đun Plug & Play.
"""

from __future__ import annotations

from typing import Optional

from config import CITY_COORDS, WMO_CODE, aqi_label
from skills.base import BaseSkill, SkillResult


class WeatherSkill(BaseSkill):
    name = "weather"
    display_name = "Thời tiết & Chất lượng không khí"
    description = (
        "Tra cứu tình hình thời tiết thời gian thực: nhiệt độ, độ ẩm, gió, khả năng mưa "
        "và chất lượng không khí (bụi mịn PM2.5 AQI) cho bất kỳ tỉnh/thành phố nào."
    )
    command = "weather"
    parameters_schema = {
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "Tên tỉnh hoặc thành phố cần xem thời tiết, ví dụ: Hà Nội, TP.HCM, Đà Nẵng, Tokyo.",
            },
        },
        "required": ["city"],
    }

    async def execute(self, city: str = "", **kwargs) -> SkillResult:
        city_clean = (city or kwargs.get("query") or "").strip()
        if not city_clean:
            return SkillResult(
                success=False,
                text="💡 Cách dùng: `/weather <thành phố>` — ví dụ `/weather Hà Nội`.",
            )

        coords = CITY_COORDS.get(city_clean.lower())
        display_name = city_clean.title()

        if not coords:
            try:
                geo_resp = await self.http_client.get(
                    "https://geocoding-api.open-meteo.com/v1/search",
                    params={"name": city_clean, "count": 1},
                    timeout=8,
                )
                geo = geo_resp.json().get("results", [])
                if not geo:
                    return SkillResult(
                        success=False,
                        text=f"❓ Không tìm thấy tỉnh thành: *{city_clean}*",
                    )
                coords = (geo[0]["latitude"], geo[0]["longitude"])
                display_name = geo[0].get("name", city_clean)
            except Exception as e:
                return SkillResult(success=False, text=f"❌ Lỗi tra cứu toạ độ: {e}")

        try:
            params = {
                "latitude": coords[0],
                "longitude": coords[1],
                "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weathercode,wind_speed_10m",
                "daily": "precipitation_probability_max,temperature_2m_max,temperature_2m_min",
                "forecast_days": 1,
                "timezone": "Asia/Bangkok",
            }
            resp = await self.http_client.get(
                "https://api.open-meteo.com/v1/forecast",
                params=params,
                timeout=8,
            )
            data = resp.json()
            cur = data.get("current", {})
            daily = data.get("daily", {})
            rain_prob = daily.get("precipitation_probability_max", [0])[0]
            t_max = daily.get("temperature_2m_max", [None])[0]
            t_min = daily.get("temperature_2m_min", [None])[0]

            aqi_line = ""
            try:
                air_resp = await self.http_client.get(
                    "https://air-quality-api.open-meteo.com/v1/air-quality",
                    params={"latitude": coords[0], "longitude": coords[1], "current": "pm2_5"},
                    timeout=6,
                )
                pm25 = air_resp.json().get("current", {}).get("pm2_5")
                aqi_line = f"🫧 Chất lượng không khí (PM2.5): *{pm25}* — {aqi_label(pm25)}\n"
            except Exception:
                pass

            report = (
                f"🌍 *Thời tiết {display_name}*\n\n{WMO_CODE.get(cur.get('weathercode'), 'Có thay đổi')}\n"
                f"🌡️ Nhiệt độ: *{cur.get('temperature_2m')}°C* (Cảm giác {cur.get('apparent_temperature')}°C)"
                + (f" • Cao nhất {t_max}°C / Thấp nhất {t_min}°C" if t_max is not None else "") + "\n"
                f"💧 Độ ẩm: {cur.get('relative_humidity_2m')}%\n"
                f"💨 Gió: {cur.get('wind_speed_10m')} km/h\n"
                f"☔ Tỉ lệ mưa: *{rain_prob}%*\n"
                f"{aqi_line}"
            )
            return SkillResult(success=True, text=report, data=data)
        except Exception as e:
            return SkillResult(success=False, text=f"❌ Lỗi thời tiết: {e}")


# ── Tương thích ngược (Backward Compatibility) ──────────────────────────────
_default_weather_skill = WeatherSkill()


def set_http_client(client):
    _default_weather_skill.set_http_client(client)
    try:
        from skills.registry import default_registry
        skill = default_registry.get("weather")
        if skill:
            skill.set_http_client(client)
    except Exception:
        pass


async def skill_weather(city: str) -> str:
    try:
        from skills.registry import default_registry
        skill = default_registry.get("weather") or _default_weather_skill
    except Exception:
        skill = _default_weather_skill
    res = await skill.execute(city=city)
    return res.text
