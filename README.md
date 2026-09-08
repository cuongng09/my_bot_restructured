# 🤖 Ollama Telegram Bot v6.2

<p align="center">
  <img src="https://img.shields.io/badge/platform-Linux%20%7C%20Windows-lightgrey" alt="Platform" />
  <img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python version" />
  <img src="https://img.shields.io/badge/status-active-brightgreen" alt="Status" />
  <img src="https://img.shields.io/badge/architecture-modular-orange" alt="Architecture" />
  <img src="https://img.shields.io/badge/license-MIT-blue" alt="License" />
</p>

<p align="center">
  <img src="bia_repo.png" alt="Telegram AI Bot Banner" width="100%" />
</p>

> **Trợ lý AI Telegram Tự Do & Mạnh Mẽ:** Tích hợp Ollama (LLM Streaming + Suy luận ẩn chuyên sâu), Hệ thống Tra cứu Web Thông minh Đa tầng (SearXNG/DuckDuckGo + Nhặt từ khóa cốt lõi + Định vị Thời gian thực), Voice 2 chiều 100% Local (faster-whisper + Piper TTS), Vision OCR & Dịch thuật Ảnh/PDF, Trí nhớ Dài hạn tự tóm tắt, Giao diện kép (Dashboard Telegram & Web App phong cách Sơn mài truyền thống).

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

### 1. Trên Linux ,Mac OS

```bash
chmod +x install.sh
./install.sh
```

### 2. Trên Windows

```powershell
Set-ExecutionPolicy Unrestricted -Scope Process
.\install.ps1
```

---

## 🎮 Danh Sách Lệnh & Thao Tác (`/commands`)

| Lệnh | Phân Quyền | Mô Tả Chức Năng |
|---|---|---|
| `/start` | Mọi người | Khởi động bot và hiển thị lời chào |
| `/help` | Mọi người | Xem hướng dẫn sử dụng chi tiết |
| `/ui` | Mọi người | Mở Trạm Điều Khiển Telegram đa cấp dạng nút bấm |
| `/weather <thành phố>` | Mọi người | Tra cứu thời tiết hiện tại & chất lượng không khí (PM2.5) |
| `/news [nguồn]` | Mọi người | Điểm tin nhanh từ `vnexpress`, `tuoitre`, `thanhnien`, `dantri`, `bbcvietnamese` |
| `/nickname <tên>` | Mọi người | Đặt tên gọi riêng để bot xưng hô thân mật |
| `/persona [tên]` | Mọi người | Đổi tính cách bot: `ban_than`, `chuyen_gia`, `hai_huoc`, `co_van` |
| `/autoweb` | Mọi người | Bật/tắt chế độ **Tự động tìm kiếm thông minh** (tự phân loại câu hỏi & nhặt từ khóa) |
| `/voice <tên>` | Mọi người | Đổi giọng đọc Piper TTS |
| `/stt <local\|groq>` | Mọi người | Đổi engine nghe giọng nói giữa `faster-whisper` và `Groq Whisper` |
| `/ttsmode <off\|smart\|always>` | Mọi người | Cấu hình chế độ trả lời bằng giọng nói |
| `/export` | Mọi người | Xuất toàn bộ lịch sử hội thoại thành file `.txt` |
| `/stop` | Mọi người | Dừng quá trình AI đang tạo câu trả lời dở dang |
| `/reset` | Mọi người | Xóa sạch ngữ cảnh trò chuyện gần đây |
| `/resetmemory` | Mọi người | Xóa sạch hồ sơ trí nhớ dài hạn (những gì bot đã nhớ về bạn) |
| `/ping` | Admin | Kiểm tra độ trễ và tình trạng kết nối tới Ollama |
| `/shutdown` | Admin | Tắt nguồn server từ xa (yêu cầu xác nhận 2 bước) |
| `/reboot` | Admin | Khởi động lại server từ xa (yêu cầu xác nhận 2 bước) |

---

## 🏗️ Cấu Trúc Mã Nguồn

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

---

## 📄 Giấy Phép (License)

Dự án được phân phối dưới giấy phép **MIT License**. Bạn có toàn quyền sử dụng, sửa đổi và đóng góp mã nguồn vì mục đích học tập cũng như thương mại.