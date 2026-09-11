"""
skills/voicebox_client.py — Tích hợp toàn diện các kỹ năng của Voicebox Docker:
  1. STT Whisper Model Management (tiny, base, small, medium, turbo)
  2. Voice Profiles (quản lý và chọn hồ sơ giọng đọc từ Voicebox)
  3. Audio Effects (hiệu ứng âm thanh: Robotic, Radio, Echo Chamber, Deep Voice)
  4. Health & System Metrics (CPU/GPU backend, trạng thái tải model)
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional
import httpx

from bot_logger import logger
from config import VOICEBOX_URL, VOICEBOX_MODEL, VOICEBOX_LANGUAGE

_http_client: Optional[httpx.AsyncClient] = None


def set_http_client(client: httpx.AsyncClient):
    global _http_client
    _http_client = client


def _get_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=15.0)
    return _http_client


# ── Health & Backend ────────────────────────────────────────────────────────
async def get_voicebox_health() -> dict[str, Any]:
    """Lấy trạng thái hệ thống Voicebox Docker."""
    client = _get_client()
    url = f"{VOICEBOX_URL.rstrip('/')}/health"
    try:
        r = await client.get(url, timeout=4.0)
        if r.status_code == 200:
            data = r.json()
            data["online"] = True
            return data
    except Exception as e:
        logger.debug(f"Voicebox health check failed: {e}")
    return {"online": False, "status": "offline"}


# ── Whisper Models ──────────────────────────────────────────────────────────
WHISPER_SIZES = ["tiny", "base", "small", "medium", "turbo"]

async def get_whisper_models_status() -> list[dict[str, Any]]:
    """Lấy danh sách các model Whisper và trạng thái tải từ Voicebox."""
    client = _get_client()
    url = f"{VOICEBOX_URL.rstrip('/')}/models/status"
    try:
        r = await client.get(url, timeout=5.0)
        if r.status_code == 200:
            all_models = r.json().get("models", [])
            whisper_models = [m for m in all_models if "whisper" in m.get("model_name", "").lower()]
            return whisper_models
    except Exception as e:
        logger.warning(f"⚠️ Không lấy được danh sách model Voicebox: {e}")
    return []


# ── Voice Profiles ──────────────────────────────────────────────────────────
async def list_voice_profiles() -> list[dict[str, Any]]:
    """Lấy danh sách hồ sơ giọng đọc (voice profiles / cloned voices) trong Voicebox."""
    client = _get_client()
    url = f"{VOICEBOX_URL.rstrip('/')}/profiles"
    try:
        r = await client.get(url, timeout=5.0)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        logger.debug(f"Không lấy được profiles Voicebox: {e}")
    return []


# ── Audio Effects Presets ───────────────────────────────────────────────────
async def list_audio_effects() -> list[dict[str, Any]]:
    """Lấy danh sách hiệu ứng âm thanh có sẵn từ Voicebox (/effects/presets)."""
    client = _get_client()
    url = f"{VOICEBOX_URL.rstrip('/')}/effects/presets"
    try:
        r = await client.get(url, timeout=5.0)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        logger.debug(f"Không lấy được presets hiệu ứng Voicebox: {e}")
    return []


# ── Chuyển đổi Whisper Model của Voicebox ───────────────────────────────────
_active_whisper_model: str = VOICEBOX_MODEL or "small"


def get_current_whisper_model() -> str:
    global _active_whisper_model
    return _active_whisper_model


def set_current_whisper_model(model_name: str) -> None:
    global _active_whisper_model
    _active_whisper_model = model_name
    logger.info(f"🎙️ Đã cập nhật model Whisper Voicebox sang: {model_name}")
