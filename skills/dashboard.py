"""
skills/dashboard.py — Skill quản trị hệ thống: thống kê CPU/RAM, ping Ollama, shutdown/reboot.
Chỉ dùng cho ADMIN_IDS.
"""

from __future__ import annotations

import os
import subprocess
import time

from bot_logger import logger
from config import OLLAMA_BASE_URL

_http_client = None


def set_http_client(client):
    global _http_client
    _http_client = client


async def skill_ping() -> str:
    t0 = time.monotonic()
    try:
        r = await _http_client.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        if r.status_code == 200:
            ms = (time.monotonic() - t0) * 1000
            n_models = len(r.json().get("models", []))
            return f"🏓 *Pong!*\n\n🦙 Ollama: ✅ OK ({ms:.0f}ms) — {n_models} model đã cài\n🗄️ Database: ✅ OK"
        return f"🏓 *Pong!*\n\n🦙 Ollama: ⚠️ HTTP {r.status_code}"
    except Exception as e:
        return (
            f"🏓 *Pong!*\n\n🦙 Ollama: ❌ Không kết nối được ({e})\n"
            f"💡 Kiểm tra `OLLAMA_BASE_URL` và Ollama đã chạy `ollama serve` chưa."
        )


async def skill_sysadmin(action: str) -> str:
    try:
        import psutil
    except ImportError:
        return "❌ Thiếu thư viện `psutil` — chạy `pip install psutil` để dùng chức năng này."

    if action == "stats":
        cpu  = psutil.cpu_percent(interval=0.5)
        ram  = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        try:
            uptime_h: int | None = int((time.time() - psutil.boot_time()) // 3600)
        except Exception:
            uptime_h = None
        uptime_line = f"• Uptime: `{uptime_h}h`\n" if uptime_h is not None else ""
        return (
            f"🖥️ *Tài nguyên máy chủ*\n"
            f"• CPU: `{cpu}%`\n"
            f"• RAM: `{ram.percent}%` ({ram.used//(1024**3)}GB / {ram.total//(1024**3)}GB)\n"
            f"• Thư mục gốc: `{disk.percent}%` đã dùng\n"
            f"{uptime_line}"
        )
    elif action == "files":
        try:
            names = os.listdir('.')[:15]
        except Exception as e:
            return f"❌ Lỗi đọc thư mục: {e}"
        return "📁 *Danh sách file thư mục:* \n`" + "`\n`".join(names) + "`" if names else "📁 Thư mục trống."
    return "Lệnh không hợp lệ."


async def run_sysaction(action: str) -> str:
    if os.name == 'nt':
        cmd = ["shutdown", "/s", "/t", "0"] if action == "shutdown" else ["shutdown", "/r", "/t", "0"]
        err_note = "💡 Đảm bảo Terminal/Command Prompt chạy bot có đủ quyền Administrator."
    else:
        cmd = ["sudo", "shutdown", "-h", "now"] if action == "shutdown" else ["sudo", "reboot"]
        err_note = "💡 Kiểm tra lại quyền `sudo` (NOPASSWD) cho user chạy bot trong `/etc/sudoers`."
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        verb = "tắt" if action == "shutdown" else "khởi động lại"
        return f"✅ Đã gửi lệnh `{' '.join(cmd)}`. Server sẽ {verb} sau vài giây..."
    except Exception as e:
        return f"❌ Lỗi khi thực thi lệnh hệ thống: {e}\n\n{err_note}"
