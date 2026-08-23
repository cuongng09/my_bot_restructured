# My Bot — Cấu trúc thư mục (v6.0, đã chia nhỏ theo tính năng)

Toàn bộ chức năng của `my_bot.py` gốc (~2050 dòng, 1 file) được giữ **nguyên vẹn**,
chỉ tách theo tính năng để dễ đọc/dễ bảo trì. `my_bot.py` giờ chỉ còn là **entrypoint**
(khởi tạo Application, đăng ký handler, wiring các module) — không còn logic nghiệp vụ.

## Cấu trúc thư mục

```
bot/
├── my_bot.py            # 🚀 ENTRYPOINT — chạy: python my_bot.py
├── config.py             # ⚙️ Toàn bộ hằng số + biến môi trường (.env)
├── bot_logger.py          # 📝 Logging tập trung (console + file xoay vòng)
├── utils.py                # 🧰 Helper dùng chung: quyền, rate-limit, safe_reply, lock...
├── llm_engine.py            # 🌐 Giao tiếp Ollama: build prompt, chat, streaming
├── database.py               # 🗄️ SQLite (giữ nguyên, không đổi)
├── reasoning.py                # 🧠 Suy luận ẩn, persona, trí nhớ dài hạn (giữ nguyên)
├── local_voice.py               # 🎙️ STT/TTS 100% local — faster-whisper + Piper (giữ nguyên)
│
├── skills/                       # 🔧 Từng tính năng độc lập, không phụ thuộc Telegram
│   ├── weather.py                  #   🌤️ Thời tiết + AQI (open-meteo)
│   ├── news.py                      #   📰 Tin tức RSS
│   ├── ocr.py                        #   🖼️ OCR ảnh/PDF + dịch 2 chiều
│   ├── web_search.py                  #   🔍 DuckDuckGo search + cào nội dung trang (RAG)
│   ├── voice.py                        #   🎙️ STT engine chọn (local/Groq) + TTS reply
│   └── dashboard.py                      #   🖥️ Sysadmin: CPU/RAM, ping, shutdown/reboot
│
├── handlers/                       # 📨 Cầu nối Telegram Update ↔ skills/
│   ├── commands.py                   #   Toàn bộ /command (trừ /ui, callback)
│   ├── text_handler.py                #   handle_text — chat streaming chính
│   ├── voice_handler.py                #   handle_voice — nhận voice note
│   ├── media_handler.py                 #   handle_media — ảnh/PDF
│   └── dashboard_handler.py              #   🏮 Trạm Điều Khiển — inline keyboard UI
│
├── webapp/                         # 🏮 Trạm Điều Khiển (bản Web) — dashboard trình duyệt
│   ├── main.py                       #   FastAPI — API đọc SQLite (read-only) + phục vụ trang tĩnh
│   └── static/
│       ├── index.html                  #   Khung trang
│       ├── style.css                    #   Hệ thống thiết kế "sơn mài" (xem bên dưới)
│       └── app.js                        #   Gọi API, tự làm mới mỗi 10s, không framework
│
├── data/                             # 🗄️ bot_data.db (SQLite) — gitignored
├── voices/                            # 🗣️ File giọng Piper (.onnx) — gitignored
├── models/                             # 🧠 Model faster-whisper tải sẵn (tùy chọn)
├── logs/                                # 📝 bot.log xoay vòng — gitignored
│
├── .env.example                          # Mẫu biến môi trường
├── .gitignore
└── requirements.txt
```

## Giao diện — hai mặt của cùng một "Trạm Điều Khiển"

Cả hai giao diện dùng chung ngôn ngữ hình ảnh/từ vựng (🏮 con dấu trạng thái đỏ-vàng,
"HOẠT ĐỘNG"/"MẤT KẾT NỐI", cùng cách gọi tên tính năng) để cảm giác như một sản phẩm,
không phải hai thứ rời rạc:

**1. Dashboard Telegram** (`handlers/dashboard_handler.py`) — bấm `/ui`:
- Kiến trúc 3 nhánh rõ ràng: 💬 Trò chuyện (mô hình/tính cách/tên gọi/giọng nói) ·
  🧰 Tiện ích (thời tiết/tin tức/dịch/tự động tìm web) · 🖥️ Hệ thống (admin).
- Cài đặt giọng nói (STT/TTS/giọng đọc) và tính cách giờ chọn bằng nút bấm thay vì
  phải nhớ cú pháp lệnh — trạng thái hiện tại luôn có dấu ✅ ngay tại chỗ.
- Mọi màn hình con đều có breadcrumb "⬅️ Quay lại <tên cha>" nhất quán.
- Trạm chính hiển thị "con dấu" 🔴/⚫ báo Ollama còn sống hay không, cộng mô hình/tính
  cách/tên gọi hiện tại — không cần đoán, không cần gõ lệnh dò trạng thái.

**2. Trạm Điều Khiển Web** (`webapp/`) — trang quản trị mới, xem trong trình duyệt:
- Thiết kế theo tinh thần **sơn mài truyền thống** (đen lacquer + son đỏ + vàng son +
  khảm trứng ngà) — một bảng cứu hoả nhỏ để chủ bot liếc qua server nhà mình, không
  phải giao diện SaaS chung chung. Dấu hiệu riêng: "con dấu" (triện) đỏ-vàng ở góc trên
  cùng, tự nhấp nháy nhẹ khi Ollama đang hoạt động.
- Hiển thị: trạng thái Ollama, CPU/RAM/ổ đĩa, số người dùng hoạt động hôm nay, bảng
  người dùng (tên gọi/mô hình/tính cách/số tin nhắn/hoạt động cuối), nhật ký gần đây
  dạng terminal.
- **Chỉ đọc** — mở kết nối SQLite riêng ở chế độ `mode=ro`, không tranh chấp khóa ghi
  với tiến trình bot, không sửa bất kỳ dữ liệu nào.
- Tự làm mới mỗi 10 giây (vanilla JS, không cần build step) — hợp với triết lý "tối
  giản, tự host" xuyên suốt cả dự án (Ollama local, STT/TTS local, OCR local...).

### Chạy Trạm Điều Khiển Web

Đây là tiến trình **RIÊNG BIỆT**, không tự chạy cùng `python my_bot.py` — cần mở thêm
một cửa sổ terminal khác:

```bash
# Terminal 1 — bot Telegram (như bình thường)
python my_bot.py

# Terminal 2 — Trạm Điều Khiển Web (chạy từ thư mục gốc bot/, nơi có config.py!)
pip install -r requirements.txt         # đã gồm fastapi + uvicorn
python -m webapp.main
```

Sau đó mở trình duyệt tại **`http://localhost:8080`** (hoặc `http://127.0.0.1:8080`).

#### Nếu không truy cập được, kiểm tra theo thứ tự:

1. **Terminal chạy `python -m webapp.main` còn mở và không báo lỗi** — nếu nó tự thoát
   ngay hoặc báo `ModuleNotFoundError: No module named 'fastapi'` → chạy
   `pip install -r requirements.txt` rồi thử lại.
2. **Chạy đúng lệnh `python -m webapp.main` từ thư mục `bot/`** (thư mục chứa
   `config.py`), KHÔNG `cd` vào trong `webapp/` rồi chạy `python main.py` — sẽ báo lỗi
   `ModuleNotFoundError: No module named 'config'`.
3. **Gõ đúng `http://localhost:8080`** trên trình duyệt — KHÔNG gõ `http://0.0.0.0:8080`.
   `WEBAPP_HOST=0.0.0.0` trong `.env` là địa chỉ để server lắng nghe, không phải địa chỉ
   để mở trên trình duyệt.
4. **Windows Firewall** có thể hiện hộp thoại hỏi cho phép `python.exe` truy cập mạng
   khi chạy lần đầu — nhớ bấm **Allow/Cho phép**, kể cả khi chỉ mở `localhost` (nếu bỏ
   qua, đôi khi Windows vẫn chặn cổng).
5. Nếu truy cập từ **máy/điện thoại khác trong cùng mạng LAN** (không phải máy đang
   chạy bot) — dùng địa chỉ IP LAN thật của máy chạy bot thay vì `localhost`, ví dụ
   `http://192.168.1.10:8080`, và đảm bảo Firewall cho phép kết nối đến từ mạng đó.

Mặc định chạy không xác thực. Nếu mở ra ngoài mạng nội bộ, **bắt buộc đặt
`WEBAPP_TOKEN`** trong `.env` để bật màn hình đăng nhập token. Đặt thêm
`WEBAPP_PUBLIC_URL` để nút "🌐 Mở Trạm Điều Khiển Web" xuất hiện trong menu Hệ thống
của `/ui` trên Telegram.



- **`skills/`** — logic nghiệp vụ thuần túy (gọi API thời tiết, tìm web, OCR...),
  **không import `telegram`**, không biết gì về Update/Context. Dễ test độc lập,
  dễ tái sử dụng nếu sau này thêm giao diện khác (Discord, Web...).
- **`handlers/`** — lớp mỏng nối Telegram Update → gọi hàm trong `skills/` → trả lời.
- **`config.py`** — nơi DUY NHẤT đọc `os.getenv()`. Mọi module khác `from config import X`.
- **HTTP client dùng chung**: khởi tạo 1 lần trong `my_bot.post_init()`, sau đó
  `inject` (qua `set_http_client()`) vào từng module cần gọi mạng — tránh mở nhiều
  connection pool lãng phí.

## Thêm tính năng mới (vd: `dictionary.py` — tra từ điển)

1. Tạo `skills/dictionary.py` — viết hàm `async def skill_dictionary(word: str) -> str`.
2. Nếu cần lệnh riêng: thêm `cmd_dictionary()` vào `handlers/commands.py`, đăng ký
   `CommandHandler("dict", cmd_dictionary)` trong `my_bot.py`.
3. Nếu cần nút trong dashboard: thêm `InlineKeyboardButton` + xử lý `data == "..."`
   trong `handlers/dashboard_handler.py`.

Không cần đụng vào các file khác — đúng tinh thần "chia nhỏ theo tính năng".

## Chạy bot

```bash
pip install -r requirements.txt
cp .env.example .env      # rồi điền TELEGRAM_TOKEN, ...
python my_bot.py
```

## Chạy tự động 24/7 trên Windows (NSSM — Windows Service)

Chạy bằng `python my_bot.py` trong 1 cửa sổ terminal chỉ tiện lúc test — máy tắt/ngủ,
đóng cửa sổ, hay mất điện là bot dừng. Muốn bot **tự khởi động cùng Windows** và
**tự hồi phục nếu crash**, dùng [NSSM](https://nssm.cc) để chạy như một Windows Service:

```powershell
# 1. Tải NSSM tại https://nssm.cc/download → giải nén bản win64
#    → copy nssm.exe vào thư mục .\scripts\ của dự án

# 2. Mở PowerShell với quyền Administrator (chuột phải → Run as administrator),
#    cd vào thư mục gốc dự án (nơi có my_bot.py), rồi chạy:
.\scripts\install_nssm_service.ps1

# Muốn cài luôn Trạm Điều Khiển Web chạy nền cùng lúc:
.\scripts\install_nssm_service.ps1 -WithWebapp
```

Script tự động: tạo service `MyBotTelegram` (và `MyBotWebapp` nếu dùng `-WithWebapp`)
chạy đúng `venv\Scripts\python.exe`, đặt `AppDirectory` về thư mục gốc (để `.env` và
đường dẫn tương đối như `data/`, `logs/` hoạt động đúng), bật tự khởi động cùng Windows,
tự restart nếu crash (chờ 5s giữa các lần), và ghi log stdout/stderr riêng vào
`logs\MyBotTelegram.out.log` / `.err.log`.

```powershell
# Kiểm tra trạng thái
Get-Service MyBotTelegram

# Xem log trực tiếp
Get-Content .\logs\bot.log -Wait -Tail 30

# Dừng / khởi động lại
nssm stop MyBotTelegram
nssm restart MyBotTelegram

# Gỡ toàn bộ service (quay lại chạy tay bằng `python my_bot.py`)
.\scripts\uninstall_nssm_service.ps1
```

⚠️ **Không chạy tay `python my_bot.py` song song khi service đã bật** — Telegram chỉ
cho 1 tiến trình poll cùng lúc, chạy 2 nơi sẽ báo lỗi `Conflict: terminated by other
getUpdates request`. Muốn chạy tay để debug, `nssm stop MyBotTelegram` trước.

## Lưu ý khi migrate từ bản 1-file cũ

- Đường dẫn DB mặc định đổi từ `bot_data.db` → `data/bot_data.db` (đã set sẵn trong
  `.env.example`). Nếu muốn giữ DB cũ, chỉnh `DB_PATH` trong `.env` trỏ về file cũ,
  hoặc copy file `.db` vào `data/`.
- Log mặc định đổi từ `bot.log` → `logs/bot.log` tương tự.
- Toàn bộ hành vi, lệnh, bug-fix trong bản gốc (concurrent_updates, user-lock,
  /stop cancel, ThinkingStreamFilter, v.v.) được giữ nguyên 100% — chỉ khác vị trí file.
