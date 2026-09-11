<div align="center">

# 🤖 Ollama Telegram Bot

### Free & Powerful Local-First AI Assistant for Telegram
### Trợ Lý AI Telegram Miễn Phí & Mạnh Mẽ — Chạy Hoàn Toàn Local

<p>
  <img src="https://img.shields.io/badge/version-6.2-blue?style=flat-square" alt="Version" />
  <img src="https://img.shields.io/badge/platform-Linux%20%7C%20Windows%20%7C%20macOS-lightgrey?style=flat-square" alt="Platform" />
  <img src="https://img.shields.io/badge/python-3.10%2B-blue?style=flat-square&logo=python&logoColor=white" alt="Python version" />
  <img src="https://img.shields.io/badge/status-active-brightgreen?style=flat-square" alt="Status" />
  <img src="https://img.shields.io/badge/architecture-modular-orange?style=flat-square" alt="Architecture" />
  <img src="https://img.shields.io/badge/license-MIT-blue?style=flat-square" alt="License" />
  <img src="https://img.shields.io/github/stars/your-username/your-repo?style=flat-square" alt="Stars" />
  <img src="https://img.shields.io/github/issues/your-username/your-repo?style=flat-square" alt="Issues" />
</p>

<img src="bia_repo.png" alt="Telegram AI Bot Banner" width="100%" />

[![English](https://img.shields.io/badge/🇬🇧-English-blue?style=for-the-badge)](#-english)
[![Tiếng Việt](https://img.shields.io/badge/🇻🇳-Tiếng_Việt-red?style=for-the-badge)](#-tiếng-việt)

*(Bấm vào nút trên để mở nhanh phần ngôn ngữ tương ứng — mỗi phần đang thu gọn, bấm tiêu đề để mở ra)*

</div>

---

## 📌 Overview / Tổng Quan

A fully **local, privacy-first** AI assistant for Telegram powered by [Ollama](https://ollama.com). It combines streaming LLM inference with hidden reasoning, a multi-layer smart web-search system, 100% offline two-way voice (faster-whisper + Piper TTS), image/PDF vision OCR with translation, self-summarizing long-term memory, and a dual dashboard (Telegram inline UI + a lacquer-styled web app).

Một trợ lý AI **chạy hoàn toàn local, ưu tiên riêng tư** cho Telegram, sử dụng [Ollama](https://ollama.com) làm lõi. Tích hợp LLM streaming với suy luận ẩn, hệ thống tra cứu web thông minh đa tầng, voice 2 chiều 100% local (faster-whisper + Piper TTS), Vision OCR & dịch thuật ảnh/PDF, trí nhớ dài hạn tự tóm tắt, và giao diện kép (Dashboard Telegram + Web App phong cách Sơn mài truyền thống).

---

<a id="-english"></a>
<details open>
<summary><h2>🇬🇧 English — click to collapse</h2></summary>

### ✨ Key Features

- **Streaming LLM Chat** — powered by any Ollama model (`llama3.1`, `qwen2.5:7b`, etc.), with hidden chain-of-thought reasoning
- **Smart Multi-Tier Web Search** — SearXNG/DuckDuckGo, automatic keyword extraction, real-time grounding
- **100% Local Voice** — two-way voice chat via faster-whisper (STT) and Piper (TTS), no cloud dependency
- **Vision OCR & Translation** — extract and translate text from images and PDFs
- **Long-Term Memory** — self-summarizing user profile memory across sessions
- **Dual Dashboard** — inline Telegram control panel + a browser-based monitoring web app
- **Weather & News** — live weather/AQI lookups and RSS news digests from major Vietnamese outlets
- **Admin Controls** — remote restart/shutdown with two-step confirmation

### 🛠️ Requirements

| Component | Requirement |
|---|---|
| Python | 3.10+ (3.11 or 3.12 recommended) |
| [Ollama](https://ollama.com) | Installed and running locally (`ollama serve`) with at least one model pulled |
| FFmpeg | Required for audio processing (`.ogg`, `.wav`, `.mp3`) used by local voice |
| Tesseract OCR | `tesseract-ocr` + language packs (`tesseract-ocr-eng`, `tesseract-ocr-vie`) |
| Piper voice model | *(optional, for local TTS)* — download a `.onnx` + `.onnx.json` voice pair from [`rhasspy/piper-voices`](https://huggingface.co/rhasspy/piper-voices), place in `./voices/`, then set `PIPER_VOICE_PATHS` in `.env` |
| Groq API Key | *(optional fallback only)* — voice defaults to local faster-whisper since v5.2; Groq Whisper is only used if explicitly switched to. All features work without a key |

> faster-whisper downloads its model automatically to cache on first run — no manual download needed.

### 📦 Installation

**Linux / macOS**

```bash
chmod +x install.sh
./install.sh
```

**Windows**

```powershell
Set-ExecutionPolicy Unrestricted -Scope Process
.\install.ps1
```

### ⚙️ Configuration

Copy `.env.example` to `.env` and fill in your values (Telegram bot token, Ollama host/model, optional Groq key, Piper voice paths, admin user IDs, etc.) before starting the bot.

```bash
cp .env.example .env
```

### 🎮 Commands

| Command | Access | Description |
|---|---|---|
| `/start` | Everyone | Start the bot and show the welcome message |
| `/help` | Everyone | Show detailed usage instructions |
| `/ui` | Everyone | Open the multi-level Telegram control panel |
| `/weather <city>` | Everyone | Get current weather & air quality (PM2.5) |
| `/news [source]` | Everyone | Quick news digest from `vnexpress`, `tuoitre`, `thanhnien`, `dantri`, `bbcvietnamese` |
| `/nickname <name>` | Everyone | Set a nickname for the bot to address you by |
| `/persona [name]` | Everyone | Switch bot personality: `ban_than`, `chuyen_gia`, `hai_huoc`, `co_van` |
| `/autoweb` | Everyone | Toggle **Smart Auto-Web Search** (auto-classifies questions & extracts keywords) |
| `/voice <name>` | Everyone | Change the Piper TTS voice |
| `/stt <local\|groq>` | Everyone | Switch speech-to-text engine between `faster-whisper` and `Groq Whisper` |
| `/ttsmode <off\|smart\|always>` | Everyone | Configure voice-reply behavior |
| `/export` | Everyone | Export full conversation history as a `.txt` file |
| `/stop` | Everyone | Stop an in-progress AI response |
| `/reset` | Everyone | Clear recent conversation context |
| `/resetmemory` | Everyone | Clear long-term memory profile |
| `/ping` | Admin | Check latency and connection status to Ollama |
| `/shutdown` | Admin | Remotely power off the server (two-step confirmation required) |
| `/reboot` | Admin | Remotely reboot the server (two-step confirmation required) |

### 🏗️ Project Structure

```text
chatAi_bots/
├── my_bot.py                 # 🚀 Entrypoint — app initialization & handler wiring
├── config.py                 # ⚙️ Environment variable loading & system constants
├── bot_logger.py              # 📝 Centralized rotating logger
├── utils.py                    # 🧰 Shared utilities: permissions, rate limiting, locks...
├── llm_engine.py                # 🧠 LLM handling: streaming, grounded RAG, real-time clock
├── database.py                   # 🗄️ SQLite management (history, settings, profiles)
├── reasoning.py                    # 💡 Question classification, hidden reasoning, memory summarization
├── local_voice.py                   # 🎙️ faster-whisper & Piper TTS engine management
│
├── skills/                           # 🔧 Independent business logic modules (Telegram-agnostic)
│   ├── web_search.py                 #    🔍 Multi-tier search, query cleanup, keyword extraction
│   ├── ocr.py                        #    🖼️ OCR text extraction & image/PDF translation
│   ├── voice.py                      #    🗣️ STT orchestration (Local/Groq) & voice reply generation
│   ├── weather.py                    #    🌤️ Weather & AQI lookup (Open-Meteo API)
│   ├── news.py                       #    📰 RSS reader for major news outlets
│   ├── pdf_report.py                 #    📄 Professional PDF research report generation
│   └── dashboard.py                  #    🖥️ Hardware resource monitoring (CPU/RAM/Disk)
│
├── handlers/                         # 📨 Telegram update receivers & dispatchers
│   ├── text_handler.py               #    Text chat handling, Smart Auto-Web trigger
│   ├── voice_handler.py              #    Incoming voice message handling
│   ├── media_handler.py              #    Image and PDF document handling
│   ├── commands.py                   #    All /command handling
│   └── dashboard_handler.py          #    Inline keyboard handling (/ui)
│
├── webapp/                           # 🏮 Web Control Station (browser dashboard)
│   ├── main.py                       #    FastAPI app — read-only monitoring API
│   └── static/                       #    Lacquer-style UI (HTML, CSS, vanilla JS)
│
├── data/                             # bot_data.db storage (auto-created)
├── voices/                           # Piper voice models (.onnx)
├── logs/                             # Rotating log files
├── requirements.txt                  # Python dependencies
└── .env.example                      # Environment configuration template
```

### 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository and create a feature branch
2. Follow the existing code style and module boundaries (`skills/` stays Telegram-agnostic)
3. Open a Pull Request with a clear description of the change

### 📄 License

Distributed under the **MIT License**. You are free to use, modify, and redistribute this project for personal, academic, or commercial purposes.

</details>

---

<a id="-tiếng-việt"></a>
<details>
<summary><h2>🇻🇳 Tiếng Việt — bấm để mở rộng</h2></summary>

### ✨ Tính Năng Nổi Bật

- **Chat LLM Streaming** — chạy trên bất kỳ model Ollama nào (`llama3.1`, `qwen2.5:7b`,...), kèm suy luận ẩn chuyên sâu
- **Tra Cứu Web Thông Minh Đa Tầng** — SearXNG/DuckDuckGo, tự nhặt từ khóa cốt lõi, định vị thời gian thực
- **Voice 2 Chiều 100% Local** — faster-whisper (STT) và Piper (TTS), không phụ thuộc cloud
- **Vision OCR & Dịch Thuật** — trích xuất và dịch chữ từ ảnh, PDF
- **Trí Nhớ Dài Hạn** — hồ sơ người dùng tự tóm tắt qua các phiên trò chuyện
- **Giao Diện Kép** — Trạm điều khiển Telegram dạng nút bấm + Web App giám sát qua trình duyệt
- **Thời Tiết & Tin Tức** — tra cứu thời tiết/AQI trực tiếp và điểm tin RSS từ các báo lớn
- **Quyền Quản Trị** — khởi động lại/tắt server từ xa với xác nhận 2 bước

### 🛠️ Yêu Cầu Hệ Thống

| Thành Phần | Yêu Cầu |
|---|---|
| Python | 3.10+ (khuyến nghị 3.11 hoặc 3.12) |
| [Ollama](https://ollama.com) | Đã cài đặt và đang chạy local (`ollama serve`) với ít nhất 1 model |
| FFmpeg | Xử lý âm thanh (`.ogg`, `.wav`, `.mp3`) cho voice local |
| Tesseract OCR | `tesseract-ocr` + gói ngôn ngữ (`tesseract-ocr-eng`, `tesseract-ocr-vie`) |
| Model giọng nói Piper | *(tùy chọn, cho TTS local)* — tải cặp file `.onnx` + `.onnx.json` từ [`rhasspy/piper-voices`](https://huggingface.co/rhasspy/piper-voices) (`vi/vi_VN/`), đặt vào `./voices/`, khai báo qua `PIPER_VOICE_PATHS` trong `.env` |
| Groq API Key | *(tùy chọn, chỉ dùng fallback)* — từ v5.2, voice mặc định chạy local; Groq Whisper chỉ dùng khi chủ động chuyển. Không có key vẫn dùng được mọi tính năng |

> faster-whisper tự động tải model vào cache khi chạy lần đầu — không cần tải tay.

### 📦 Cài Đặt

**Trên Linux / macOS**

```bash
chmod +x install.sh
./install.sh
```

**Trên Windows**

```powershell
Set-ExecutionPolicy Unrestricted -Scope Process
.\install.ps1
```

### ⚙️ Cấu Hình

Sao chép `.env.example` thành `.env` và điền các giá trị cần thiết (token bot Telegram, host/model Ollama, key Groq nếu có, đường dẫn giọng Piper, ID admin,...) trước khi khởi chạy bot.

```bash
cp .env.example .env
```

### 🎮 Danh Sách Lệnh

| Lệnh | Phân Quyền | Mô Tả Chức Năng |
|---|---|---|
| `/start` | Mọi người | Khởi động bot và hiển thị lời chào |
| `/help` | Mọi người | Xem hướng dẫn sử dụng chi tiết |
| `/ui` | Mọi người | Mở Trạm Điều Khiển Telegram đa cấp dạng nút bấm |
| `/weather <thành phố>` | Mọi người | Tra cứu thời tiết hiện tại & chất lượng không khí (PM2.5) |
| `/news [nguồn]` | Mọi người | Điểm tin nhanh từ `vnexpress`, `tuoitre`, `thanhnien`, `dantri`, `bbcvietnamese` |
| `/nickname <tên>` | Mọi người | Đặt tên gọi riêng để bot xưng hô thân mật |
| `/persona [tên]` | Mọi người | Đổi tính cách bot: `ban_than`, `chuyen_gia`, `hai_huoc`, `co_van` |
| `/autoweb` | Mọi người | Bật/tắt chế độ **Tự động tìm kiếm thông minh** |
| `/voice <tên>` | Mọi người | Đổi giọng đọc Piper TTS |
| `/stt <local\|groq>` | Mọi người | Đổi engine nghe giọng nói giữa `faster-whisper` và `Groq Whisper` |
| `/ttsmode <off\|smart\|always>` | Mọi người | Cấu hình chế độ trả lời bằng giọng nói |
| `/export` | Mọi người | Xuất toàn bộ lịch sử hội thoại thành file `.txt` |
| `/stop` | Mọi người | Dừng quá trình AI đang tạo câu trả lời dở dang |
| `/reset` | Mọi người | Xóa sạch ngữ cảnh trò chuyện gần đây |
| `/resetmemory` | Mọi người | Xóa sạch hồ sơ trí nhớ dài hạn |
| `/ping` | Admin | Kiểm tra độ trễ và tình trạng kết nối tới Ollama |
| `/shutdown` | Admin | Tắt nguồn server từ xa (yêu cầu xác nhận 2 bước) |
| `/reboot` | Admin | Khởi động lại server từ xa (yêu cầu xác nhận 2 bước) |

### 🏗️ Cấu Trúc Mã Nguồn

```text
chatAi_bots/
├── my_bot.py                 # 🚀 Entrypoint — Khởi tạo Application & liên kết handler
├── config.py                  # ⚙️ Nạp biến môi trường (.env) & hằng số hệ thống
├── bot_logger.py               # 📝 Quản lý logging xoay vòng tập trung
├── utils.py                     # 🧰 Các tiện ích phụ trợ: phân quyền, rate limit, locks...
├── llm_engine.py                 # 🧠 Xử lý LLM: Streaming, Grounded RAG, Realtime Clock
├── database.py                    # 🗄️ Quản trị CSDL SQLite (lịch sử, cài đặt, profile)
├── reasoning.py                     # 💡 Phân loại câu hỏi, suy luận ẩn, tóm tắt trí nhớ dài hạn
├── local_voice.py                    # 🎙️ Quản lý engine faster-whisper và Piper TTS local
│
├── skills/                            # 🔧 Các module nghiệp vụ độc lập (Không phụ thuộc Telegram)
│   ├── web_search.py                  #    🔍 Tìm kiếm đa tầng, làm sạch query, nhặt từ khóa cốt lõi
│   ├── ocr.py                         #    🖼️ OCR trích xuất chữ và dịch thuật ảnh/PDF
│   ├── voice.py                       #    🗣️ Điều phối STT (Local/Groq) và tạo voice reply
│   ├── weather.py                     #    🌤️ Tra cứu thời tiết & AQI (Open-Meteo API)
│   ├── news.py                        #    📰 Đọc RSS các báo điện tử hàng đầu
│   ├── pdf_report.py                  #    📄 Tạo báo cáo nghiên cứu dạng PDF chuyên nghiệp
│   └── dashboard.py                   #    🖥️ Giám sát tài nguyên phần cứng (CPU/RAM/Disk)
│
├── handlers/                          # 📨 Bộ tiếp nhận & điều phối sự kiện Telegram Update
│   ├── text_handler.py                #    Xử lý chat văn bản, kích hoạt Smart Auto-Web
│   ├── voice_handler.py               #    Xử lý tin nhắn thoại đầu vào
│   ├── media_handler.py               #    Xử lý hình ảnh và tài liệu PDF
│   ├── commands.py                    #    Xử lý toàn bộ lệnh /command
│   └── dashboard_handler.py           #    Xử lý giao diện Inline Keyboard (/ui)
│
├── webapp/                            # 🏮 Trạm Điều Khiển Web (Dashboard trình duyệt)
│   ├── main.py                        #    FastAPI App — Cung cấp API giám sát read-only
│   └── static/                        #    Giao diện phong cách Sơn mài (HTML, CSS, JS thuần)
│
├── data/                              # Nơi lưu bot_data.db (tự động tạo)
├── voices/                            # Nơi chứa các model giọng đọc Piper (.onnx)
├── logs/                              # Nơi lưu trữ file log xoay vòng
├── requirements.txt                   # Danh sách thư viện phụ thuộc
└── .env.example                       # Mẫu cấu hình môi trường
```

### 🤝 Đóng Góp

Rất hoan nghênh mọi đóng góp! Vui lòng:
1. Fork repository và tạo branch riêng cho tính năng mới
2. Tuân thủ style code hiện có và ranh giới module (`skills/` không phụ thuộc Telegram)
3. Mở Pull Request kèm mô tả rõ ràng về thay đổi

### 📄 Giấy Phép

Dự án được phân phối dưới giấy phép **MIT License**. Bạn có toàn quyền sử dụng, sửa đổi và đóng góp mã nguồn vì mục đích học tập cũng như thương mại.

</details>

---

<div align="center">

Made with ❤️ using Ollama · Được tạo với ❤️ bằng Ollama

</div>