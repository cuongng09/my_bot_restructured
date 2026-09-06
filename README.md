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

## 🌟 Tính Năng Nổi Bật

### 1. 🧠 Trí Tuệ Nhân Tạo & Suy Luận Chuyên Sâu
- **Phản hồi siêu tốc dạng dòng (Streaming):** Trả lời từng từ mượt mà theo thời gian thực, hỗ trợ hủy tác vụ đang tạo dở với `/stop`.
- **Suy luận ẩn (Hidden Chain-of-Thought):** Tự động phân loại câu hỏi phức tạp (toán học, lập trình, phân tích đa chiều) để ép mô hình "suy nghĩ ngầm" trong thẻ `<suy_nghi>` trước khi xuất kết quả chính thức; lọc sạch phần suy nghĩ bằng `ThinkingStreamFilter`.
- **4 Persona linh hoạt:** Chuyển đổi giọng điệu nhanh chóng giữa `ban_than` (Bạn thân), `chuyen_gia` (Chuyên gia), `hai_huoc` (Hài hước) và `co_van` (Cố vấn chiến lược).
- **Hồ sơ & Trí nhớ dài hạn:** Tự động đúc kết thói quen, sở thích của người dùng sau mỗi 10 lượt trò chuyện để cá nhân hóa câu trả lời mà không làm phình ngữ cảnh (hỗ trợ xóa riêng với `/resetmemory`).

### 2. 🌐 Hệ Thống Tìm Kiếm Thông Minh Đa Tầng & Thời Gian Thực (Smart Web RAG)
- **Nguồn tìm kiếm linh hoạt:** Ưu tiên instance **SearXNG** tự host (bảo mật, không bị rate-limit) kết hợp dự phòng **DuckDuckGo API (DDGS)** và cào HTML trực tiếp.
- **Tiền lọc ý định siêu tốc (Fast Heuristic Intent Filter):** Nhận diện lập tức các câu chào hỏi, viết code, giải toán, sáng tác, tâm sự để phản hồi ngay bằng kho tri thức bách khoa của AI, không gọi tìm kiếm web vô ích.
- **Tối ưu hóa câu truy vấn (Query Reformulation):** Tự động bóc tách ngôn ngữ tự nhiên thành từ khóa tìm kiếm Google/DuckDuckGo chuẩn mực.
- **Cơ chế "Nhặt từ khóa cốt lõi" (Adaptive Keyword Extraction & Retry):** Khi câu hỏi công nghệ dài hoặc phức tạp không ra kết quả ban đầu, hệ thống tự động loại bỏ từ bổ nghĩa, bảo toàn số phiên bản phần mềm (như `3.7`, `3.14`, `5090`) để tìm lại, hỗ trợ truy vấn công nghệ quốc tế theo thời gian thực (`<core_query> latest update`).
- **Định vị Thời Gian Thực (Real-time Clock Anchor - GMT+7):** Cung cấp mốc ngày, giờ thực tế cho mô hình; đối chiếu dữ liệu tìm được với tri thức AI để phân tích các lĩnh vực biến đổi từng giờ (AI, phần mềm, công nghệ mới), **chấm dứt hoàn toàn phản hồi cộc lốc "không có dữ liệu"**.
- **Bảo mật & Ưu tiên nguồn tin cậy:** Sắp xếp nguồn ưu tín lên đầu (VnExpress, Tuổi Trẻ, Báo Chính Phủ, WHO, Wikipedia...) và trang bị **SSRF Guard** ngăn chặn bot truy cập các địa chỉ IP nội bộ độc hại.

### 3. 🎙️ Đàm Thoại Giọng Nói 100% Local (Không Cần API Ngoài)
- **Nghe (STT):** Sử dụng `faster-whisper` chạy trực tiếp trên máy chủ (CPU/GPU), hỗ trợ nhận diện tiếng Việt chính xác cao và tự động dự phòng sang Groq Whisper API nếu có cấu hình.
- **Nói (TTS):** Chuyển văn bản thành giọng nói tiếng Việt mượt mà qua `Piper TTS` với các model ONNX gọn nhẹ.
- **3 Chế độ Voice Reply (`/ttsmode`):** `off` (chỉ gửi text), `smart` (tự động phát âm thanh với câu trả lời ngắn/vừa), `always` (luôn trả lời bằng voice).

### 4. 🖼️ Thị Giác OCR & Dịch Thuật Đa Định Dạng
- **Hỗ trợ Ảnh & PDF:** Trích xuất chữ tự động từ file ảnh (JPG, PNG, WebP) và tài liệu PDF (cả PDF dạng scan và PDF có lớp text).
- **Tự động nhận diện ngôn ngữ:** Tự động phát hiện tiếng Việt hoặc tiếng Anh và dịch hai chiều chuẩn xác.

### 5. 🏮 Giao Diện Kép: Telegram Dashboard & Web App Sơn Mài
- **Trạm Điều Khiển Telegram (`/ui`):** Menu Inline Keyboard đa cấp chia 3 nhánh: 💬 Trò chuyện · 🧰 Tiện ích · 🖥️ Hệ thống. Đổi model Ollama, đổi giọng đọc, đổi persona trực quan bằng nút bấm.
- **Trạm Điều Khiển Web (`webapp/`):** Dashboard quản trị trình duyệt viết bằng FastAPI + Vanilla JS, thiết kế theo ngôn ngữ **Sơn mài truyền thống** (đen lacquer, son đỏ, khảm vàng). Theo dõi trạng thái Ollama theo thời gian thực (con dấu nhấp nháy), thống kê phần cứng CPU/RAM/Disk, người dùng hoạt động và nhật ký terminal trực tiếp.

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

Repo đi kèm 2 script cài đặt tự động, thực hiện toàn bộ các bước cần thiết (dependency hệ
thống, venv, `requirements.txt`, tạo `.env`, hỏi `TELEGRAM_TOKEN`, kiểm tra Ollama, và
tùy chọn cài Docker + triển khai SearXNG):

### 1. Trên Linux (Ubuntu / Debian)

```bash
chmod +x install.sh
./install.sh
```

### 2. Trên Windows

```powershell
Set-ExecutionPolicy Unrestricted -Scope Process
.\install.ps1
```

Sau khi script chạy xong, khởi chạy bot bằng:

```bash
# Linux/macOS
source venv/bin/activate && python3 my_bot.py
```
```powershell
# Windows
.\venv\Scripts\Activate.ps1 ; python my_bot.py
```

---

## 🏮 Trạm Điều Khiển Web (Dashboard)

Repo đi kèm một dashboard quản trị chạy trên trình duyệt (`webapp/`), dùng FastAPI + Uvicorn.
Thư viện cần thiết (`fastapi`, `uvicorn`) **đã nằm sẵn trong `requirements.txt`** — không cần cài
thêm gì nếu bạn đã làm bước `pip install -r requirements.txt` ở trên.

1. Cấu hình (tùy chọn) trong `.env` — đã có sẵn giá trị mặc định hợp lý:

```env
WEBAPP_HOST=0.0.0.0     # địa chỉ SERVER lắng nghe (0.0.0.0 = mọi card mạng)
WEBAPP_PORT=8080
WEBAPP_TOKEN=           # để trống = không xác thực; điền 1 chuỗi bất kỳ để bật đăng nhập token
```

2. Chạy thử — **luôn chạy từ thư mục gốc `chatAi_bots/`** (nơi có `config.py`), độc lập với `my_bot.py`:

```bash
# Linux/macOS (đã kích hoạt venv)
python -m webapp.main
```

```powershell
# Windows (đã kích hoạt venv)
python -m webapp.main
```

3. Mở trình duyệt tại `http://localhost:8080` (không gõ `0.0.0.0:8080`, sẽ không kết nối được).

Webapp chỉ đọc dữ liệu (SQLite ở chế độ read-only), không tranh chấp với tiến trình bot, nên có thể
chạy song song với `my_bot.py` mà không lo xung đột. Xem cách chạy **tự động cùng hệ thống** ở phần
[Khởi Chạy Bot](#-khởi-chạy-bot) bên dưới.

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
WorkingDirectory=/home/cwng/Documents/GitHub/my_bot_restructured/chatAi_bots
ExecStart=/home/cwng/Documents/GitHub/my_bot_restructured/chatAi_bots/venv/bin/python3 /home/cwng/Documents/GitHub/my_bot_restructured/chatAi_bots/my_bot.py
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

Muốn Trạm Điều Khiển Web cũng tự khởi động cùng hệ thống, tạo thêm 1 service riêng
`/etc/systemd/system/telegram-bot-webapp.service` (chạy độc lập, không tranh chấp gì với bot):

```ini
[Unit]
Description=Telegram AI Bot - Web Dashboard
After=network.target telegram-bot.service

[Service]
Type=simple
WorkingDirectory=/home/cwng/Documents/GitHub/my_bot_restructured/chatAi_bots
ExecStart=/home/cwng/Documents/GitHub/my_bot_restructured/chatAi_bots/venv/bin/python3 -m webapp.main
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot-webapp.service
sudo systemctl start telegram-bot-webapp.service
sudo systemctl status telegram-bot-webapp.service
```

> Nhớ sửa `WorkingDirectory` và đường dẫn `venv` trong cả 2 file `.service` cho khớp với thư mục
> dự án thật trên máy bạn (mặc định ở trên chỉ là ví dụ).

### 3. Chạy dưới dạng Windows Service (NSSM - script tự động, khuyến nghị)

Repo đã có sẵn script PowerShell tự động hoá toàn bộ việc cài NSSM cho **cả bot lẫn webapp** —
không cần điền tay qua giao diện NSSM nữa.

1. Mở PowerShell với quyền **Administrator**, di chuyển vào thư mục gốc dự án (`chatAi_bots/`):

```powershell
cd C:\Users\<tên-bạn>\...\my_bot_restructured\chatAi_bots
```

2. Đảm bảo đã có `venv\` (đã tạo ở bước Cài Đặt) và có `nssm.exe` — repo đã kèm sẵn `nssm.exe`
   ở thư mục gốc, hoặc bạn có thể copy bản khác vào `.\scripts\nssm.exe`.

3. Chạy script cài đặt — thêm `-WithWebapp` để cài luôn service cho Trạm Điều Khiển Web:

```powershell
.\scripts\install_nssm_service.ps1 -WithWebapp
```

Script sẽ tự động:
- Tạo service **MyBotTelegram** (`python my_bot.py`) và **MyBotWebapp** (`python -m webapp.main`).
- Trỏ đúng `venv\Scripts\python.exe` và thư mục dự án làm `AppDirectory`.
- Bật tự khởi động cùng Windows (`SERVICE_AUTO_START`) và tự restart nếu crash.
- Ghi log riêng (có xoay vòng) vào `logs\MyBotTelegram.out.log` / `logs\MyBotWebapp.out.log`.
- Tự khởi động cả 2 service ngay sau khi cài xong.

> ⚠️ Sau khi cài service, **không chạy tay** `python my_bot.py` nữa — sẽ bị Telegram báo lỗi
> Conflict vì 2 tiến trình cùng poll 1 token. Dùng lệnh NSSM để dừng trước nếu cần chạy tay.

Các lệnh quản lý tiện lợi về sau (PowerShell Admin):

```powershell
Get-Service MyBotTelegram, MyBotWebapp        # xem trạng thái
nssm restart MyBotTelegram                    # khởi động lại bot
nssm restart MyBotWebapp                      # khởi động lại webapp
nssm stop MyBotTelegram                       # dừng bot (để chạy tay tạm thời)
Get-Content .\logs\bot.log -Wait -Tail 30      # xem log trực tiếp

# Gỡ toàn bộ service khi cần
.\scripts\uninstall_nssm_service.ps1
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