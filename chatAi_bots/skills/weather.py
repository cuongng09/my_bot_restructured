"""
skills/weather.py — Thời tiết + chất lượng không khí (open-meteo, không cần API key).
"""

from __future__ import annotations

from typing import Optional

from config import CITY_COORDS, WMO_CODE, aqi_label

# HTTP client được inject từ my_bot.post_init
_http_client = None


def set_http_client(client):
    global _http_client
    _http_client = client


async def skill_weather(city: str) -> str:
    city_clean = city.strip()
    coords = CITY_COORDS.get(city_clean.lower())
    display_name = city_clean.title()

    if not coords:
        try:
            geo_resp = await _http_client.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": city_clean, "count": 1}, timeout=8,
            )
            geo = geo_resp.json().get("results", [])
            if not geo:
                return f"❓ Không tìm thấy tỉnh thành: *{city_clean}*"
            coords = (geo[0]["latitude"], geo[0]["longitude"])
            display_name = geo[0].get("name", city_clean)
        except Exception as e:
            return f"❌ Lỗi: {e}"

    try:
        params = {
            "latitude": coords[0], "longitude": coords[1],
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weathercode,wind_speed_10m",
            "daily": "precipitation_probability_max,temperature_2m_max,temperature_2m_min",
            "forecast_days": 1, "timezone": "Asia/Bangkok",
        }
        resp = await _http_client.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=8)
        data = resp.json()
        cur   = data.get("current", {})
        daily = data.get("daily", {})
        rain_prob = daily.get("precipitation_probability_max", [0])[0]
        t_max = daily.get("temperature_2m_max", [None])[0]
        t_min = daily.get("temperature_2m_min", [None])[0]

        aqi_line = ""
        try:
            air_resp = await _http_client.get(
                "https://air-quality-api.open-meteo.com/v1/air-quality",
                params={"latitude": coords[0], "longitude": coords[1], "current": "pm2_5"},
                timeout=6,
            )
            pm25 = air_resp.json().get("current", {}).get("pm2_5")
            aqi_line = f"🫧 Chất lượng không khí (PM2.5): *{pm25}* — {aqi_label(pm25)}\n"
        except Exception:
            pass

        return (
            f"🌍 *Thời tiết {display_name}*\n\n{WMO_CODE.get(cur.get('weathercode'), 'Có thay đổi')}\n"
            f"🌡️ Nhiệt độ: *{cur.get('temperature_2m')}°C* (Cảm giác {cur.get('apparent_temperature')}°C)"
            + (f" • Cao nhất {t_max}°C / Thấp nhất {t_min}°C" if t_max is not None else "") + "\n"
            f"💧 Độ ẩm: {cur.get('relative_humidity_2m')}%\n"
            f"💨 Gió: {cur.get('wind_speed_10m')} km/h\n"
            f"☔ Tỉ lệ mưa: *{rain_prob}%*\n"
            f"{aqi_line}"
        )
    except Exception as e:
        return f"❌ Lỗi: {e}"
