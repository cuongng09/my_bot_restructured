# 🤖 Ollama Telegram Bot v5.2

<p align="center">
  <img src="https://img.shields.io/badge/platform-Linux%20%7C%20Windows-lightgrey" alt="Platform" />
  <img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python version" />
  <img src="https://img.shields.io/github/issues/USERNAME/REPO?color=orange&label=issues" alt="Issues" />
  <img src="https://img.shields.io/badge/status-active-brightgreen" alt="Status" />
  <img src="https://img.shields.io/github/license/USERNAME/REPO?color=blue" alt="License" />
</p>

<p align="center">
  <a href="https://github.com/USERNAME/REPO">
    <img src="https://img.shields.io/github/stars/USERNAME/REPO?style=social" alt="Follow" />
  </a>
</p>

<p align="center">
  <img src="bia_repo.png" alt="Telegram AI Bot Banner" width="100%" />
</p>

> **Trợ lý AI Telegram siêu tốc & đa năng:** Tích hợp Ollama (LLM Streaming + suy luận ẩn cho câu hỏi phức tạp), Vision OCR & Dịch thuật Ảnh/PDF, Voice hai chiều 100% local (faster-whisper + Piper TTS), trí nhớ dài hạn tự tóm tắt, 4 persona chọn được, Web Search thời gian thực có trích dẫn nguồn kèm link, SQLite Storage & UI Dashboard tương tác đa cấp.

---

## 🛠️ Yêu Cầu Hệ Thống

1. **Python:** 3.10+ (Khuyến nghị Python 3.11 hoặc 3.12)
2. **Ollama:** Đã cài đặt và đang chạy local (`ollama serve`) với mô hình sẵn có (VD: `llama3.1`, `qwen2.5:7b`, v.v.)
3. **Hệ thống Dependencies (Cài trên hệ điều hành):**
   - **FFmpeg:** Xử lý & chuyển đổi file âm thanh (`.ogg`, `.wav`, `.mp3`) — dùng cho cả voice local (faster-whisper/Piper).
   - **Tesseract OCR:** Trích chữ từ hình ảnh (cần package `tesseract-ocr` và ngôn ngữ `tesseract-ocr-eng` / `tesseract-ocr-vie`).
4. **Model giọng nói Piper** *(bắt buộc nếu muốn TTS local)*: tải 2 file `.onnx` + `.onnx.json` của 1 giọng tiếng Việt bất kỳ từ kho [`rhasspy/piper-voices`](https://huggingface.co/rhasspy/piper-voices) (thư mục `vi/vi_VN/`), đặt vào `./voices/` rồi khai báo qua `PIPER_VOICE_PATHS` trong `.env`. faster-whisper thì **không cần tải tay** — tự tải model vào cache khi chạy lần đầu.
5. **Groq API Key** *(tùy chọn, chỉ dùng làm fallback)*: kể từ v5.2, voice mặc định chạy local (faster-whisper); Groq Whisper chỉ còn là phương án dự phòng nếu bạn chủ động chuyển lại. Không có key vẫn chạy được mọi tính năng.

---

## 📦 Cài Đặt

### 1. Trên Linux (Ubuntu / Debian)

1. Sao chép mã nguồn vào thư mục dự án.
2. Cập nhật hệ thống và cài đặt các dependency:

```bash
sudo apt update
sudo apt install python3-full python3-pip ffmpeg -y
sudo apt install tesseract-ocr tesseract-ocr-eng
sudo apt-get install -y tesseract-ocr tesseract-ocr-vie
```

> 🎙️ Sau khi cài `requirements.txt` (bước dưới), tải model giọng Piper tiếng Việt (làm 1 lần) từ kho [`rhasspy/piper-voices`](https://huggingface.co/rhasspy/piper-voices) và đặt vào `./voices/` — xem chi tiết ở [`UPGRADE_GUIDE.md`](./UPGRADE_GUIDE.md#0-cài-thêm-thư-viện).

3. Tạo và kích hoạt môi trường ảo, cài thư viện, kiểm thử:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 my_bot.py
deactivate
```

### 2. Trên Windows

1. Cài đặt các công cụ cần thiết:

```powershell
# 1. Cài đặt Python
winget install --id Python.Python.3.11 -e

# 2. Cài đặt FFmpeg
winget install --id Gyan.FFmpeg -e

# 3. Cài đặt Tesseract OCR
winget install --id UB-Mannheim.TesseractOCR -e
```

2. Tạo môi trường ảo:

```powershell
python -m venv venv
Set-ExecutionPolicy Unrestricted -Scope Process
.\venv\Scripts\Activate.ps1
python.exe -m pip install --upgrade pip
pip install -r requirements.txt
```

3. Khởi chạy bot:

```powershell
python my_bot.py
```

---

## 🚀 Khởi Chạy Bot

### 1. Chạy Trực Tiếp

```bash
# Kích hoạt venv nếu chưa kích hoạt
source venv/bin/activate  # Trên Linux/macOS
# Khởi chạy bot
python my_bot.py
```

### 2. Chạy dưới dạng Dịch Vụ Systemd (Linux - Khuyến nghị)

Tạo file dịch vụ `/etc/systemd/system/telegram-bot.service`:

```ini
[Unit]
Description=Telegram AI Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/cwng/Documents/GitHub/chatAi_bots
ExecStart=/home/cwng/Documents/GitHub/chatAi_bots/venv/bin/python3 /home/cwng/Documents/GitHub/chatAi_bots/my_bot.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Kích hoạt và khởi động dịch vụ:

```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot.service
sudo systemctl start telegram-bot.service
sudo systemctl status telegram-bot.service
sudo systemctl restart telegram-bot.service
```

### 3. Chạy dưới dạng Dịch Vụ Windows Service (NSSM - Khuyến nghị)

1. Trỏ về đúng thư mục dự án:

```powershell
cd C:\Users\ngcwn\OneDrive\Documents\GitHub\my_bot_restructured\chatAi_bots
```

2. Gọi lệnh cài đặt Service:

```powershell
.\nssm.exe install TelegramBotService
```

3. Điền bảng thông số NSSM GUI. Một cửa sổ bảng điều khiển NSSM sẽ bật lên, điền chính xác từng mục:

- **Tab 1 — Path:** Nhấp `...` và trỏ đến đúng file `python.exe` trong môi trường ảo:
  ```powershell
  C:\C:\Users\ngcwn\OneDrive\Documents\GitHub\my_bot_restructured\chatAi_bots\venv\Scripts\python.exe
  ```
- **Tab 2 — Startup directory:** Trỏ đến thư mục chứa code:
  ```powershell
  C:\C:\Users\ngcwn\OneDrive\Documents\GitHub\my_bot_restructured\chatAi_bots
  ```
- **Tab 3 — Arguments:** Điền tên file chính:
  ```powershell
  my_bot.py
  ```

4. Khởi chạy và kiểm tra Service:

```powershell
.\nssm.exe start TelegramBotService
```

Các lệnh quản lý Bot tiện lợi về sau (chạy trên PowerShell Admin):

```powershell
.\nssm.exe status TelegramBotService
.\nssm.exe restart TelegramBotService
.\nssm.exe stop TelegramBotService
.\nssm.exe remove TelegramBotService confirm
```

---

## 🎮 Lệnh & Hướng Dẫn Sử Dụng

### 📜 Danh Sách Lệnh (`/commands`)

| Lệnh | Mô tả |
|---|---|
| `/start` | Khởi động bot và hiển thị lời chào |
| `/help` | Xem hướng dẫn sử dụng đầy đủ |
| `/ui` | Mở Dashboard UI đa cấp (chọn model, tiện ích, quản trị) |
| `/weather <thành phố>` | Tra cứu thời tiết hiện tại + chất lượng không khí (PM2.5) |
| `/news [nguồn]` | Điểm tin nhanh — `vnexpress` (mặc định), `tuoitre`, `thanhnien`, `dantri`, `bbcvietnamese` |
| `/nickname <tên>` | Đặt tên gọi riêng để bot xưng hô gần gũi hơn |
| `/persona <tên>` | Đổi tính cách/giọng văn bot — `ban_than`, `chuyen_gia`, `hai_huoc`, `co_van` |
| `/voice <tên>` | Đổi giọng đọc Piper khi bot trả lời bằng voice (xem danh sách qua `PIPER_VOICE_PATHS`) |
| `/export` | Xuất toàn bộ lịch sử hội thoại ra file `.txt` |
| `/stop` | Dừng phản hồi AI đang tạo dở giữa chừng |
| `/reset` | Xóa sạch lịch sử hội thoại cá nhân trong CSDL |
| `/autoweb` | Bật/tắt tự động tra cứu web thời gian thực cho **mọi** tin nhắn (chữ + thoại) |
| `/ping` | Kiểm tra tình trạng kết nối tới Ollama |
| `/shutdown` | *[Admin]* Tắt nguồn server — cần xác nhận 2 bước |
| `/reboot` | *[Admin]* Khởi động lại server — cần xác nhận 2 bước |

> 💡 Nếu không bật `/autoweb`, bot vẫn tự động tra web khi câu hỏi chứa các từ khóa như "giá vàng", "tỷ giá", "mới nhất", "bây giờ", "hôm nay".

---

## 🏗️ Cấu Trúc Dự Án

```text
.
bot/
├── my_bot.py            # Entrypoint — chạy: python my_bot.py
├── config.py             # Toàn bộ hằng số + biến môi trường (.env)
├── bot_logger.py          # Logging tập trung (console + file xoay vòng)
├── utils.py                # Helper dùng chung: quyền, rate-limit, safe_reply, lock...
├── llm_engine.py            # Giao tiếp Ollama: build prompt, chat, streaming
├── database.py               # SQLite (giữ nguyên)
├── reasoning.py                # Suy luận ẩn, persona, trí nhớ dài hạn (giữ nguyên)
├── local_voice.py               # STT/TTS local — faster-whisper + Piper (giữ nguyên)
│
├── skills/                       # Tính năng độc lập, KHÔNG import telegram
│   ├── weather.py                  # Thời tiết + AQI (open-meteo)
│   ├── news.py                      # Tin tức RSS
│   ├── ocr.py                        # OCR ảnh/PDF + dịch 2 chiều
│   ├── web_search.py                  # DuckDuckGo search + cào nội dung (RAG)
│   ├── voice.py                        # STT (local/Groq) + TTS reply
│   └── dashboard.py                     # Sysadmin: CPU/RAM, ping, shutdown/reboot
│
├── handlers/                       # Cầu nối Telegram Update ↔ skills/
│   ├── commands.py                   # Toàn bộ /command (trừ /ui, callback)
│   ├── text_handler.py                # handle_text — chat streaming chính
│   ├── voice_handler.py                # handle_voice — nhận voice note
│   ├── media_handler.py                 # handle_media — ảnh/PDF
│   └── dashboard_handler.py              # Inline keyboard UI + callback_query
│
├── data/       # bot_data.db (SQLite) — gitignored
├── voices/      # File giọng Piper (.onnx) — gitignored
├── models/       # Model faster-whisper tải sẵn (tùy chọn)
├── logs/          # bot.log xoay vòng — gitignored
│
├── .env.example    # Mẫu biến môi trường
├── .gitignore
└── requirements.txt
```

---

## 📝 Giấy Phép

Dự án phát triển dưới giấy phép **MIT License**. Mọi đóng góp và Pull Request đều được hoan nghênh!