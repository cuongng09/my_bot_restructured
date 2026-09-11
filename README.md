# 🤖 Ollama Telegram Bot v7.0

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

> **Trợ lý AI Telegram tự do, chạy 100% local:** Tích hợp Ollama (LLM Streaming + Suy luận ẩn), Tìm kiếm Thông minh Đa tầng mặc định (SearXNG + DuckDuckGo + RAG từ khóa cốt lõi), Voice 2 chiều qua **Voicebox Docker** (Whisper STT + Piper TTS), Phản hồi 2 tầng (Câu đầu trọng tâm + Tự động xuất **Word / Excel** không bị vỡ bảng), Vision OCR & Dịch thuật Ảnh/PDF, Trí nhớ Dài hạn, Giao diện kép (Dashboard Telegram `/ui` + **Web App** Dark Glassmorphism).

---

## ✨ Tính Năng Nổi Bật

### 🔍 Tìm kiếm Thông minh Đa tầng (Mặc định cho mọi tin nhắn)
- **Bộ lọc ý định tức thì** — Nhận biết chào hỏi, code, toán học, sáng tác → trả lời ngay bằng tri thức AI, không tốn tài nguyên tìm kiếm.
- **LLM phân tích & trích xuất query** — Tự nhận diện câu hỏi thời sự, giá cả, công nghệ mới nhất và cô đọng thành 2–6 từ khóa nòng cốt.
- **Multi-layer Fallback** — SearXNG cục bộ → DuckDuckGo API → Cào HTML sâu (Trafilatura) → Dịch truy vấn sang tiếng Anh.
- **Xếp hạng nguồn tin cậy** — Ưu tiên `vnexpress.net`, `tuoitre.vn`, `thanhnien.vn`, `dantri.com.vn` và báo chính thống.

### 💬 Phản hồi 2 Tầng — Câu đầu trọng tâm + File Word/Excel
- Telegram chỉ hiển thị **1–3 câu mở đầu trọng tâm** + gợi ý `📄 Thông tin chi tiết được đính kèm trong tệp bên dưới`.
- **Tự động xuất Excel (`.xlsx`)** khi phản hồi có bảng số liệu, so sánh — cột chuẩn, viền ô, zebra striping, tiêu đề navy.
- **Tự động xuất Word (`.docx`)** khi phản hồi là lịch trình, kế hoạch, phân tích chi tiết — callout box, bảng nhúng, font Arial.
- Trong quá trình stream: hiển thị câu mở đầu trọng tâm kèm `⏳ Đang xử lý nội dung chi tiết vào tệp...` — chat không bị tràn chữ.

### 🎙️ Voicebox Studio (STT + TTS)
- **STT qua Voicebox Docker** (Whisper) — chuyển giọng nói thành văn bản hoàn toàn local, không gửi lên cloud.
- **Đổi model Whisper động** ngay trong `/ui`: `tiny`, `base`, `small`, `medium`, `turbo` — không cần restart.
- **TTS qua Piper** — tổng hợp giọng tiếng Việt chất lượng cao, offline hoàn toàn.
- **Hiệu ứng âm thanh** — `Robotic`, `Radio`, `Echo Chamber`, `Deep Voice` tích hợp sẵn trong Voicebox.
- **Voice Reply thông minh** — Chỉ đọc câu đầu trọng tâm, không đọc bảng biểu hay URL. Thời gian TTS giảm từ ~30s xuống **2–5 giây**.

### 🏮 Web Dashboard (Dark Glassmorphism — `http://localhost:8080`)
- Card **Voicebox Studio**: trạng thái Docker, Whisper model đang nạp, danh sách profiles & audio effects.
- Card **Tệp Báo Cáo & Dữ Liệu**: danh sách `.docx`/`.xlsx` đã xuất với nút **Tải về** trực tiếp trên trình duyệt.
- Card thống kê: CPU/RAM/Disk, Uptime, Ollama model, bảng người dùng Telegram.
- Bảo mật bằng `WEBAPP_TOKEN` (Bearer header / localStorage).

### 🧰 Tiện Ích Khác
- 🌤️ **Thời tiết** — Nhiệt độ, độ ẩm, AQI (PM2.5) — Submenu riêng trong `/ui → Tiện ích → Thời tiết`.
- 📰 **Tin tức** — RSS VnExpress, Tuổi Trẻ, Thanh Niên, Dân Trí, BBC Tiếng Việt — Submenu riêng trong `/ui`.
- 🖼️ **Vision OCR** — Trích xuất chữ từ ảnh (Tesseract) & dịch thuật ảnh/PDF.
- 🧠 **Trí nhớ Dài hạn** — Tóm tắt hồ sơ người dùng định kỳ bằng LLM (tên, sở thích, phong cách).
- 💡 **Suy luận ẩn** — Câu hỏi phức tạp được bọc `<suy_nghi>` để LLM suy luận nội tâm trước khi trả lời.
- 📤 **Xuất lịch sử** — Export toàn bộ hội thoại thành file `.txt`.

---

## 📦 Cài Đặt

### Linux / macOS

```bash
chmod +x chatAi_bots/install.sh
cd chatAi_bots
./install.sh
```

### Windows

```powershell
Set-ExecutionPolicy Unrestricted -Scope Process
cd chatAi_bots
.\install.ps1
```

---

## 🚀 Khởi Động Dịch Vụ

### Bot Telegram (systemd)

```bash
systemctl status telegram-bot.service     # Xem trạng thái
sudo systemctl restart telegram-bot.service  # Khởi động lại sau khi cập nhật code
journalctl -u telegram-bot.service -f     # Xem log trực tiếp
```

### SearXNG

```bash
docker compose -f docker-compose.yml up -d
# → http://localhost:8081
```

### Web Dashboard

```bash
docker compose -f docker-compose.webapp.yml up -d --build
# → http://localhost:8080
```

### Voicebox

```bash
cd chatAi_bots/voicebox && just dev-backend
# → http://localhost:17600 (map từ container port 17493)
```

---

## 🎮 Danh Sách Lệnh

| Lệnh | Phân quyền | Mô tả |
|---|---|---|
| `/start` | Mọi người | Lời chào & tóm tắt tính năng |
| `/help` | Mọi người | Hướng dẫn sử dụng chi tiết |
| `/ui` | Mọi người | Mở Trạm Điều Khiển Telegram (menu nút bấm đa cấp) |
| `/weather <thành phố>` | Mọi người | Tra thời tiết & AQI theo thành phố |
| `/news [nguồn]` | Mọi người | Điểm tin từ `vnexpress`, `tuoitre`, `thanhnien`, `dantri`, `bbcvietnamese` |
| `/nickname <tên>` | Mọi người | Đặt tên gọi riêng để bot xưng hô thân mật |
| `/persona [tên]` | Mọi người | Đổi tính cách bot: `ban_than`, `chuyen_gia`, `hai_huoc`, `co_van` |
| `/voice <tên>` | Mọi người | Đổi giọng đọc Piper TTS |
| `/stt <local\|groq>` | Mọi người | Chuyển engine STT giữa Voicebox local và Groq Whisper cloud |
| `/ttsmode <off\|smart\|always>` | Mọi người | Cấu hình chế độ phản hồi bằng giọng nói |
| `/export` | Mọi người | Xuất toàn bộ lịch sử hội thoại thành `.txt` |
| `/stop` | Mọi người | Dừng quá trình AI đang sinh câu trả lời |
| `/reset` | Mọi người | Xóa ngữ cảnh trò chuyện gần đây |
| `/resetmemory` | Mọi người | Xóa hồ sơ trí nhớ dài hạn |
| `/ping` | Admin | Kiểm tra độ trễ kết nối tới Ollama |
| `/shutdown` | Admin | Tắt server từ xa (xác nhận 2 bước) |
| `/reboot` | Admin | Khởi động lại server từ xa (xác nhận 2 bước) |

> **Lưu ý:** `/autoweb` không còn cần thiết — tìm kiếm thông minh đa tầng là **mặc định vĩnh viễn** cho mọi tin nhắn.

---

## 🏗️ Cấu Trúc Mã Nguồn

```text
chatAi_bots/
├── my_bot.py                   # 🚀 Entrypoint — Khởi tạo Application & liên kết handler
├── config.py                   # ⚙️ Nạp biến môi trường (.env) & hằng số hệ thống
├── bot_logger.py               # 📝 Logging xoay vòng tập trung
├── utils.py                    # 🧰 Phân quyền, rate limit, locks, history
├── llm_engine.py               # 🧠 LLM streaming, Grounded RAG, quyết định tìm kiếm web
├── database.py                 # 🗄️ SQLite — lịch sử, cài đặt, hồ sơ người dùng
├── reasoning.py                # 💡 Suy luận ẩn, phân loại câu hỏi, tóm tắt trí nhớ dài hạn
├── local_voice.py              # 🎙️ Quản lý Voicebox STT & Piper TTS local
│
├── skills/                     # 🔧 Module nghiệp vụ độc lập
│   ├── web_search.py           #    🔍 Tìm kiếm đa tầng (SearXNG + DDGS + RAG HTML sâu)
│   ├── document_exporter.py    #    📊 Xuất Word (.docx) / Excel (.xlsx) tự động, chống vỡ bảng
│   ├── voicebox_client.py      #    🎛️ REST client tới Voicebox Docker API (Whisper + Effects)
│   ├── voice.py                #    🗣️ Điều phối STT/TTS & voice reply thông minh
│   ├── ocr.py                  #    🖼️ OCR ảnh/PDF & dịch thuật (Tesseract + Google Translate)
│   ├── weather.py              #    🌤️ Thời tiết & AQI (Open-Meteo API)
│   ├── news.py                 #    📰 Đọc RSS báo điện tử hàng đầu Việt Nam
│   ├── pdf_report.py           #    📄 Tạo báo cáo nghiên cứu PDF chuyên nghiệp
│   └── dashboard.py            #    🖥️ Giám sát CPU/RAM/Disk phần cứng (psutil)
│
├── handlers/                   # 📨 Xử lý sự kiện Telegram Update
│   ├── text_handler.py         #    Chat văn bản (stream + tìm kiếm + phân tách + xuất file)
│   ├── voice_handler.py        #    Tin nhắn thoại (STT → LLM → TTS)
│   ├── media_handler.py        #    Hình ảnh & tài liệu PDF (OCR/Vision)
│   ├── commands.py             #    Toàn bộ lệnh /command
│   └── dashboard_handler.py    #    Inline Keyboard /ui (Voicebox Studio, Tiện ích, Hệ thống...)
│
├── webapp/                     # 🏮 Trạm Điều Khiển Web (Dark Glassmorphism)
│   ├── main.py                 #    FastAPI — API giám sát, tải báo cáo, Voicebox status
│   └── static/                 #    HTML/CSS/JS thuần — không framework
│
├── data/
│   ├── bot_data.db             # SQLite (tự động tạo)
│   └── reports/                # Thư mục Word/Excel xuất ra (tự động tạo)
├── voices/                     # Model Piper TTS (.onnx + .onnx.json)
├── logs/                       # File log xoay vòng
├── docker-compose.yml          # SearXNG + Valkey (Redis)
├── docker-compose.webapp.yml   # Web Dashboard Docker
├── Dockerfile.webapp           # Image Docker cho webapp
├── requirements.txt            # Python dependencies
├── install.sh                  # Script cài đặt Linux/macOS
├── install.ps1                 # Script cài đặt Windows
└── .env.example                # Mẫu cấu hình môi trường
```

---

## 📄 Giấy Phép (License)

Dự án được phân phối dưới giấy phép **MIT License**. Bạn có toàn quyền sử dụng, sửa đổi và đóng góp mã nguồn vì mục đích học tập cũng như thương mại.
