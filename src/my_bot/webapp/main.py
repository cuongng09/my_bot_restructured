"""Read-only text bot dashboard."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import aiosqlite
import httpx
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from my_bot.config import (
    ADMIN_IDS, ALLOWED_IDS, DB_PATH, DEFAULT_MODEL, OLLAMA_BASE_URL,
    WEBAPP_HOST, WEBAPP_PORT, WEBAPP_TOKEN,
)

STATIC_DIR = Path(__file__).parent / "static"
app = FastAPI(title="my_bot text dashboard", docs_url=None, redoc_url=None)
app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")


def _check_token(token: Optional[str]) -> None:
    if WEBAPP_TOKEN and token != WEBAPP_TOKEN:
        raise HTTPException(status_code=401, detail="Sai hoặc thiếu token quản trị.")


async def _open_db() -> Optional[aiosqlite.Connection]:
    path = Path(DB_PATH)
    if not path.exists():
        return None
    try:
        return await aiosqlite.connect(f"file:{path}?mode=ro", uri=True)
    except aiosqlite.Error:
        return None


@app.get("/api/status")
async def api_status(x_admin_token: Optional[str] = Header(None)):
    _check_token(x_admin_token)
    alive, models = False, []
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
            alive = response.status_code == 200
            if alive:
                models = [item["name"] for item in response.json().get("models", [])]
    except httpx.HTTPError:
        pass
    return {
        "ollama_alive": alive,
        "models": models,
        "default_model": DEFAULT_MODEL,
        "allowed_users_count": len(ALLOWED_IDS) or None,
        "admin_users_count": len(ADMIN_IDS),
        "server_time": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/stats")
async def api_stats(x_admin_token: Optional[str] = Header(None)):
    _check_token(x_admin_token)
    conn = await _open_db()
    if conn is None:
        return {"total_users": 0, "active_today": 0, "total_messages": 0, "ready": False}
    try:
        start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        async with conn.execute("SELECT COUNT(DISTINCT uid), COUNT(*) FROM history") as cursor:
            total_users, total_messages = await cursor.fetchone()
        async with conn.execute("SELECT COUNT(DISTINCT uid) FROM history WHERE ts >= ?", (start,)) as cursor:
            active_today = (await cursor.fetchone())[0]
        return {
            "total_users": total_users,
            "active_today": active_today,
            "total_messages": total_messages,
            "ready": True,
        }
    finally:
        await conn.close()


@app.get("/api/users")
async def api_users(x_admin_token: Optional[str] = Header(None)):
    _check_token(x_admin_token)
    conn = await _open_db()
    if conn is None:
        return {"users": []}
    try:
        query = """
        SELECT h.uid, MAX(h.ts), COUNT(h.id), s.nickname, s.model, s.persona, s.auto_web
        FROM history h LEFT JOIN settings s ON s.uid = h.uid
        GROUP BY h.uid ORDER BY MAX(h.ts) DESC
        """
        async with conn.execute(query) as cursor:
            rows = await cursor.fetchall()
        return {"users": [
            {
                "uid": row[0], "last_active": row[1], "msg_count": row[2],
                "nickname": row[3], "model": row[4] or DEFAULT_MODEL,
                "persona": row[5] or "ban_than", "auto_web": bool(row[6]),
                "is_admin": row[0] in ADMIN_IDS,
            }
            for row in rows
        ]}
    finally:
        await conn.close()


@app.get("/api/logs")
async def api_logs(x_admin_token: Optional[str] = Header(None)):
    _check_token(x_admin_token)
    return {"lines": []}


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


def run_server() -> None:
    import uvicorn
    uvicorn.run(app, host=WEBAPP_HOST, port=WEBAPP_PORT, log_level="info")


if __name__ == "__main__":
    run_server()
