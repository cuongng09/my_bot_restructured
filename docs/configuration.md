# Hướng Dẫn Cấu Hình `my_bot`

Tất cả các tham số cấu hình của bot được quản lý tập trung trong file `.env` ở thư mục gốc của dự án. Mẫu cấu hình chuẩn có tại `.env.example`.

## 1. Cấu Hình Bắt Buộc

| Biến | Ý nghĩa | Ví dụ |
|---|---|---|
| `TELEGRAM_TOKEN` | Token API được cấp bởi `@BotFather` | `123456:ABC-DEF...` |

## 2. Kết Nối Ollama

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Địa chỉ dịch vụ Ollama |
| `OLLAMA_MODEL` | `qwen2.5:7b` | Tên mô hình LLM mặc định |
| `OLLAMA_TIMEOUT_SEC` | `240` | Timeout cho các yêu cầu sinh nội dung (giây) |
| `OLLAMA_CONTEXT_SIZE` | `8192` | Kích thước Context Window cấp phát cho LLM |

## 3. Phân Quyền & Hành Vi

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `ALLOWED_USERS` | *(để trống = tất cả)* | Danh sách Telegram User ID được phép dùng bot, cách nhau bởi dấu phẩy |
| `ADMIN_USER_IDS` | *(để trống)* | Danh sách Telegram User ID có quyền Admin (`/shutdown`, `/reboot`, system stats) |
| `RATE_LIMIT_SEC` | `3` | Khoảng thời gian giãn cách tối thiểu giữa 2 yêu cầu liên tiếp |
| `MAX_HISTORY` | `25` | Số tin nhắn gần nhất lưu trong bộ nhớ ngữ cảnh |

## 4. Voice Pipeline (STT & TTS)

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `GROQ_API_KEY` | *(để trống)* | Khóa API Groq dùng cho STT Whisper đám mây |
| `VOICEBOX_URL` | `http://127.0.0.1:17600` | Địa chỉ Voicebox STT Docker |
| `VOICEBOX_MODEL` | `small` | Mô hình Whisper nội bộ của Voicebox |
| `PIPER_VOICE_PATHS` | `nu:./voices/...` | Đường dẫn file mô hình giọng đọc Piper ONNX |

## 5. Trạm Điều Khiển Web (FastAPI)

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `WEBAPP_HOST` | `0.0.0.0` | Địa chỉ lắng nghe của máy chủ Web |
| `WEBAPP_PORT` | `8080` | Cổng HTTP |
| `WEBAPP_TOKEN` | *(để trống)* | Token bảo vệ màn hình quản trị Web |
| `WEBAPP_PUBLIC_URL`| *(để trống)* | URL công khai để mở từ nút bấm Telegram trong `/ui` |

