"""
webapp/main.py — 🏮 TRẠM ĐIỀU KHIỂN (bản Web): API + phục vụ trang tĩnh cho dashboard quản trị.

Chạy ĐỘC LẬP với tiến trình bot (đọc chung 1 file SQLite ở chế độ read-only, không tranh
chấp khóa ghi với bot). Không sửa bất kỳ dữ liệu nào — thuần túy hiển thị số liệu.

⚠️ QUAN TRỌNG — không tự chạy cùng `my_bot.py`, phải khởi động RIÊNG bằng lệnh dưới đây,
   và BẮT BUỘC chạy từ thư mục gốc `bot/` (nơi có file `config.py`), không phải từ trong
   thư mục `webapp/`:

    cd bot                       # thư mục gốc, chứa my_bot.py + config.py
    python -m webapp.main

Sau khi chạy, mở trình duyệt tại  http://localhost:8080  (hoặc http://127.0.0.1:8080).
LƯU Ý: nếu .env có WEBAPP_HOST=0.0.0.0, đó là địa chỉ để SERVER lắng nghe — KHÔNG gõ
"0.0.0.0:8080" trên trình duyệt, nó sẽ không kết nối được. Luôn dùng localhost/127.0.0.1
(hoặc IP LAN thật của máy nếu truy cập từ thiết bị khác trong cùng mạng).

Bảo mật: nếu đặt WEBAPP_TOKEN trong .env, mọi endpoint /api/* yêu cầu header
`X-Admin-Token: <token>` — trang index.html tự hỏi token và lưu vào localStorage khi cần.
Để trống WEBAPP_TOKEN = chạy không xác thực (chỉ nên làm vậy sau reverse-proxy/VPN riêng).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import aiosqlite
import httpx
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from config import (
    DB_PATH, LOG_FILE, OLLAMA_BASE_URL, DEFAULT_MODEL,
    ALLOWED_IDS, ADMIN_IDS, WEBAPP_TOKEN, WEBAPP_HOST, WEBAPP_PORT,
)

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Trạm Điều Khiển", docs_url=None, redoc_url=None)
app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")


# ─────────────────────────────────────────────────────────────────────────────
# 🔐 Xác thực đơn giản qua header
# ─────────────────────────────────────────────────────────────────────────────
def _check_token(x_admin_token: Optional[str]):
    if WEBAPP_TOKEN and x_admin_token != WEBAPP_TOKEN:
        raise HTTPException(status_code=401, detail="Sai hoặc thiếu token quản trị.")


# ─────────────────────────────────────────────────────────────────────────────
# 🗄️ Đọc SQLite (read-only, tách biệt hoàn toàn khỏi tiến trình bot)
# ─────────────────────────────────────────────────────────────────────────────
async def _open_db() -> Optional[aiosqlite.Connection]:
    db_path = Path(DB_PATH)
    if not db_path.exists():
        return None
    try:
        conn = await aiosqlite.connect(f"file:{db_path}?mode=ro", uri=True)
        return conn
    except Exception:
        return None


@app.get("/api/status")
async def api_status(x_admin_token: Optional[str] = Header(None)):
    _check_token(x_admin_token)

    ollama_alive, models = False, []
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
            if r.status_code == 200:
                ollama_alive = True
                models = [m["name"] for m in r.json().get("models", [])]
    except Exception:
        pass

    cpu = ram_percent = disk_percent = uptime_h = None
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.3)
        ram_percent = psutil.virtual_memory().percent
        disk_percent = psutil.disk_usage("/").percent
        uptime_h = round((datetime.now().timestamp() - psutil.boot_time()) / 3600, 1)
    except ImportError:
        pass

    return JSONResponse({
        "ollama_alive": ollama_alive,
        "models": models,
        "default_model": DEFAULT_MODEL,
        "cpu": cpu,
        "ram_percent": ram_percent,
        "disk_percent": disk_percent,
        "uptime_hours": uptime_h,
        "allowed_users_count": len(ALLOWED_IDS) or None,   # None = mở cho tất cả
        "admin_users_count": len(ADMIN_IDS),
        "server_time": datetime.now(timezone.utc).isoformat(),
    })


@app.get("/api/stats")
async def api_stats(x_admin_token: Optional[str] = Header(None)):
    _check_token(x_admin_token)
    conn = await _open_db()
    if conn is None:
        return JSONResponse({"total_users": 0, "active_today": 0, "total_messages": 0, "ready": False})

    try:
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ).isoformat()

        async with conn.execute("SELECT COUNT(DISTINCT uid) FROM history") as cur:
            total_users = (await cur.fetchone())[0]
        async with conn.execute(
            "SELECT COUNT(DISTINCT uid) FROM history WHERE ts >= ?", (today_start,)
        ) as cur:
            active_today = (await cur.fetchone())[0]
        async with conn.execute("SELECT COUNT(*) FROM history") as cur:
            total_messages = (await cur.fetchone())[0]

        return JSONResponse({
            "total_users": total_users,
            "active_today": active_today,
            "total_messages": total_messages,
            "ready": True,
        })
    finally:
        await conn.close()


@app.get("/api/users")
async def api_users(limit: int = 100, x_admin_token: Optional[str] = Header(None)):
    _check_token(x_admin_token)
    conn = await _open_db()
    if conn is None:
        return JSONResponse({"users": []})

    try:
        query = """
            SELECT h.uid, MAX(h.ts) AS last_active, COUNT(h.id) AS msg_count,
                   s.nickname, s.model, s.persona, s.auto_web
            FROM history h
            LEFT JOIN settings s ON s.uid = h.uid
            GROUP BY h.uid
            ORDER BY last_active DESC
            LIMIT ?
        """
        users = []
        async with conn.execute(query, (limit,)) as cur:
            async for row in cur:
                users.append({
                    "uid": row[0],
                    "last_active": row[1],
                    "msg_count": row[2],
                    "nickname": row[3],
                    "model": row[4] or DEFAULT_MODEL,
                    "persona": row[5] or "ban_than",
                    "auto_web": bool(row[6]),
                    "is_admin": row[0] in ADMIN_IDS,
                })
        return JSONResponse({"users": users})
    finally:
        await conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# 📝 Nhật ký gần đây (tail log file)
# ─────────────────────────────────────────────────────────────────────────────
_LOG_LINE_RE = re.compile(r"^(?P<ts>[\d\-]+ [\d:,]+) \| (?P<level>\w+) \| (?P<name>[\w.]+) \| (?P<msg>.*)$")


@app.get("/api/logs")
async def api_logs(limit: int = 80, x_admin_token: Optional[str] = Header(None)):
    _check_token(x_admin_token)
    log_path = Path(LOG_FILE)
    if not log_path.exists():
        return JSONResponse({"lines": []})

    try:
        raw_lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return JSONResponse({"lines": []})

    tail = raw_lines[-limit:]
    parsed = []
    for line in tail:
        m = _LOG_LINE_RE.match(line)
        if m:
            parsed.append(m.groupdict())
        elif line.strip():
            parsed.append({"ts": "", "level": "INFO", "name": "", "msg": line})
    return JSONResponse({"lines": parsed})


# ─────────────────────────────────────────────────────────────────────────────
# 🖼️ Trang tĩnh
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


def main():
    import uvicorn
    # Truyền thẳng object `app` (thay vì chuỗi "webapp.main:app") — tránh phải re-import
    # bằng đường dẫn module, vốn dễ lỗi nếu chạy không đúng từ thư mục gốc bot/.
    logger_print = f"🏮 Trạm Điều Khiển Web đang chạy tại: http://localhost:{WEBAPP_PORT}  (Ctrl+C để dừng)"
    print(logger_print)
    uvicorn.run(app, host=WEBAPP_HOST, port=WEBAPP_PORT, log_level="info")


if __name__ == "__main__":
    main()
