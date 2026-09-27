# my_bot — Bản text-only (làm lại rút gọn)

Tài liệu này là spec làm lại **chỉ chat văn bản**. Không ảnh, không voice, không Voicebox, không OCR, không xuất Word/Excel/PDF.

Bản đầy đủ (có media/voice/file) nằm ở `README.md`. Khi implement theo file này: **không** mang các module đã liệt kê ở mục “Loại bỏ”.

---

## 1. Phạm vi

Giữ:

- Chat text streaming với Ollama
- Ngữ cảnh hội thoại, persona, nickname, trí nhớ dài hạn
- RAG web: SearXNG rồi DuckDuckGo, cache, SSRF, nguồn ưu tín
- Suy luận ẩn cho câu phức tạp; `/stop`
- Skills text: thời tiết, tin tức, crypto
- Dashboard Telegram `/ui` (nút bấm, không menu giọng nói)
- Web FastAPI read-only (tuỳ chọn)
- Rate limit, whitelist, lock theo user
- `/export` lịch sử dạng **.txt**

Bỏ hẳn:

- Voice note, STT, TTS, Piper, gTTS, faster-whisper, Groq Whisper
- Voicebox (Docker, `just`, bun, clone repo)
- Ảnh, PDF, OCR, Tesseract, dịch từ ảnh
- `document_exporter` (Word, Excel)
- `pdf_report` (báo cáo PDF)
- Lệnh `/voice`, `/stt`, `/ttsmode`
- Handler voice/media
- Dependency: ffmpeg (nếu chỉ text), tesseract, piper-tts, faster-whisper, groq, gTTS, python-docx, openpyxl, reportlab, pytesseract, Pillow, pypdf

---

## 2. Nguyên tắc

- Package `src/my_bot/`, import `from my_bot...`
- Entrypoint mỏng: `main.py` chỉ đăng ký handler
- Config một cửa: `config.py`
- Skills plug-and-play, auto-discover
- Async: PTB 21+, httpx dùng chung, aiosqlite WAL
- Installer chạy từ **root repo** (không từ `scripts/`)
- Blocking chỉ còn DDGS search → thread executor

---

## 3. Kiến trúc

```
Telegram (text) --> Bot PTB --> Ollama :11434
                      |  |
                      |  +--> SearXNG :8081 (optional) / DuckDuckGo
                      +--> SQLite WAL (data/bot_data.db)

WebApp FastAPI :8080  --> đọc SQLite mode=ro (process riêng)
```

Luồng tin nhắn:

1. Whitelist + mention nhóm + rate limit
2. Lock theo uid
3. Lưu history user
4. Nếu auto_web: heuristic rồi LLM quyết định search
5. Search (nếu cần) → grounded messages + token budget
6. Nếu câu phức tạp: wrap hidden CoT
7. Stream Ollama → lọc `<suy_nghi>` → edit Telegram
8. Gửi text + footer nguồn (nếu có web)
9. Lưu history assistant; mỗi N lượt tóm tắt hồ sơ nền

Không tách bảng ra file Word/Excel. Câu dài: `split_message` nhiều tin Telegram.

---

## 4. Cấu trúc thư mục

```
src/my_bot/
  __init__.py
  __main__.py
  main.py
  config.py
  core/
    logger.py
    database.py
    llm_engine.py
    reasoning.py
    context_manager.py
    utils.py
  handlers/
    commands.py
    text_handler.py
    dashboard_handler.py
  skills/
    base.py
    registry.py
    weather.py
    news.py
    web_search.py
    extra/crypto.py
  webapp/                    # tuỳ chọn
    main.py
    static/                  # HTML/CSS/JS — không nhúng ảnh banner bắt buộc
pyproject.toml
.env.example
Dockerfile
docker-compose.yml           # bot + webapp + searxng — không voicebox
scripts/install.sh
scripts/uninstall.sh
scripts/systemd/my_bot.service
tests/
data/  logs/
```

Không có: `local_voice.py`, `tencent_memory.py` (bỏ trừ khi cần sau), `voice_handler.py`, `media_handler.py`, `ocr.py`, `voice.py`, `voicebox_client.py`, `document_exporter.py`, `pdf_report.py`, `voices/`, `fonts/` (PDF).

CLI:

```
my-bot = my_bot.main:main
my-bot-web = my_bot.webapp.main:run_server
```

---

## 5. Stack

- Python 3.11+
- python-telegram-bot >= 21, `concurrent_updates=True`
- httpx, python-dotenv, aiosqlite
- duckduckgo-search, beautifulsoup4, trafilatura, langdetect
- fastapi, uvicorn, psutil (webapp/dashboard)
- Ollama trên máy host

Hệ thống: Python, pip, venv. Không bắt Tesseract/ffmpeg/Voicebox.

---

## 6. Cài đặt (rút gọn)

Thứ tự `install.sh` (ROOT = thư mục có `pyproject.toml`):

1. Nhận OS: Debian/Fedora/RHEL/Arch/openSUSE/macOS
2. Cài python3 + venv (không tesseract, không ffmpeg)
3. `.venv` + `pip install -e ".[dev]"`
4. Copy `.env.example` → `.env`, hỏi `TELEGRAM_TOKEN`
5. `mkdir -p data logs`
6. Kiểm tra `ollama` (thiếu thì cảnh báo, không fail)
7. Hỏi Docker; hỏi SearXNG port 8081, `settings.yml` phải có `json`
8. Hỏi webapp Docker (không hỏi Voicebox)
9. Linux: hỏi systemd — `ExecStart=.../.venv/bin/python -m my_bot`

Windows: venv + pip + NSSM, không bash installer.

Docker Compose chỉ: `bot`, `webapp`, `searxng`. Không service `voicebox`. Rewrite `localhost` Ollama → `host.docker.internal` trong container.

---

## 7. Biến môi trường

Bắt buộc: `TELEGRAM_TOKEN`.

Giữ: timeout Telegram, Ollama, `ALLOWED_USERS`, `ADMIN_USER_IDS`, `MAX_HISTORY`, `RATE_LIMIT_SEC`, `REQUIRE_MENTION_IN_GROUPS`, `LONG_TERM_MEMORY_EVERY_N_TURNS`, `STREAM_EDIT_INTERVAL`, `DB_PATH`, `LOG_FILE`, `SEARXNG_URL`, `SEARCH_CACHE_TTL_SEC`, `TRUSTED_DOMAINS*`, `WEBAPP_*`.

Xóa khỏi `.env.example` và `config.py`:

- `GROQ_*`, `VOICEBOX_*`, `PIPER_*`
- `TESSERACT_CMD`, `OCR_LANG`, `MAX_UPLOAD_MB` (không upload media)
- `PDF_*`, `REPORTS_OUTPUT_DIR`

Hằng số còn lại: tọa độ thành phố, WMO, RSS, từ khóa search/so sánh.

---

## 8. SQLite

Bảng: `history`, `settings`, `rate_limit`, `user_chat_status_logs`, `search_cache`. WAL + ALTER cột thiếu.

`settings` **bỏ** cột: `voice_mode`, `stt_engine`, `tts_voice`, `media_mode`.

Giữ: `model`, `auto_web`, `nickname`, `persona`, `profile_summary`, `turns_since_summary`.

---

## 9. Core

**utils:** allowed/admin, mention nhóm, split 4000 ký tự, lock, `ACTIVE_GEN_TASKS`, history helpers.

**llm_engine:** cache models; `decide_web_search`; `build_grounded_messages` (persona, giờ VN GMT+7, hồ sơ, nickname, khối web, cấm tự viết nguồn); stream; `clean_model_generated_sources`.

**reasoning:** complexity; hidden CoT; `ThinkingStreamFilter`; 4 persona `ban_than` / `chuyen_gia` / `hai_huoc` / `co_van`; tóm tắt hồ sơ.

**context_manager:** cắt history/web cho vừa `OLLAMA_CONTEXT_SIZE`.

Không `local_voice`.

---

## 10. Web search

Cache hash → SearXNG JSON → DDG fallback → rank trusted → SSRF chặn private/loopback/metadata → crawl tối đa 3 trang → format context + footer. Tắt bot: shutdown executor.

---

## 11. Skills còn lại

`BaseSkill` + `SkillResult` (không dùng `file_path` cho Word/Excel).

| Skill | Lệnh | Ghi chú |
|---|---|---|
| weather | `/weather <thành phố>` | Open-Meteo, AQI |
| news | `/news [nguồn]` | RSS |
| crypto | `/crypto [BTC]` | Binance |
| web_search | nội bộ | auto_web / LLM |

Lệnh lõi không trùng dispatcher: `start help ui reset resetmemory stop export nickname persona ping weather news autoweb shutdown reboot`.

Không đăng ký skill voice/ocr/pdf.

---

## 12. Handler và lệnh

Chỉ: `CommandHandler` + `CallbackQueryHandler` + `MessageHandler(TEXT & ~COMMAND)`.

Không handler VOICE/AUDIO/PHOTO/Document.

| Lệnh | Việc |
|---|---|
| `/start` `/help` | Text, trỏ `/ui` |
| `/ui` | Model, persona, auto_web, weather, news, (admin) ping/shutdown |
| `/reset` `/resetmemory` `/stop` | Như bản đầy đủ |
| `/export` | File **.txt** |
| `/nickname` `/persona` | |
| `/ping` `/shutdown` `/reboot` | Admin |
| `/weather` `/news` `/autoweb` | |

`/ui` không có nút giọng nói / STT / TTS / dịch ảnh.

Text handler: không gọi `split_core_and_detail` / exporter. Stream xong gửi (cắt nhiều tin nếu cần) + footer URL.

---

## 13. WebApp (tuỳ chọn)

Read-only. Token header nếu `WEBAPP_TOKEN` set.

API giữ: `/api/status`, `/api/stats`, `/api/users`, `/api/logs`.

API bỏ: `/api/voicebox`, `/api/reports`, download file.

Giao diện: chữ và số liệu, không phụ thuộc ảnh banner hay Voicebox.

---

## 14. Dependencies mục tiêu (`pyproject.toml`)

```
python-telegram-bot>=21
httpx
python-dotenv
aiosqlite
beautifulsoup4
duckduckgo-search
trafilatura
langdetect
fastapi
uvicorn[standard]
psutil
```

Dev: pytest, pytest-asyncio.

---

## 15. Test tối thiểu

- Import `my_bot`
- Discover `weather`, `news`, `crypto`
- Token budget cắt history
- `should_trigger_web_search` / `extract_final_answer`
- SSRF chặn `127.0.0.1`
- Không import `voice`, `ocr`, `document_exporter`

---

## 16. Checklist implement

1. Package `src/my_bot/` + pyproject CLI
2. config + logger + database (settings không cột voice)
3. llm / reasoning / context / utils
4. skills weather, news, crypto, web_search
5. commands + text + `/ui` (không media/voice)
6. webapp rút API
7. install.sh không Voicebox/tesseract/ffmpeg
8. compose không voicebox
9. pytest

---

## 17. Chạy

```
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# điền TELEGRAM_TOKEN, ALLOWED_USERS, ADMIN_USER_IDS
ollama pull qwen2.5:7b
my-bot
```

Docker: `docker compose up -d --build` (bot + searxng + webapp).
