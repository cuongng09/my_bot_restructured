#!/usr/bin/env bash
# =====================================================================
#  install.sh — Cài đặt nhanh Ollama Telegram Bot v6.2 (Linux/Ubuntu/Debian)
#  Dựa theo hướng dẫn trong README.md của dự án.
#
#  Cách dùng:
#     chmod +x install.sh
#     ./install.sh
# =====================================================================

set -e  # Dừng script ngay nếu có lệnh lỗi

# ---- Màu sắc cho log cho dễ nhìn ----
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[!!]${NC} $1"; }
err()  { echo -e "${RED}[LỖI]${NC} $1"; }

# ---- 0. Kiểm tra hệ điều hành ----
if [[ "$(uname)" != "Linux" ]]; then
    err "Script này chỉ dành cho Linux (Ubuntu/Debian). Với Windows hãy làm theo phần 'Trên Windows' trong README.md."
    exit 1
fi

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"
log "Thư mục dự án: $PROJECT_DIR"

# ---- 1. Cài dependency hệ thống ----
log "Đang cập nhật hệ thống và cài dependency (cần quyền sudo)..."
sudo apt update
sudo apt install -y python3-full python3-pip python3-venv ffmpeg
sudo apt install -y tesseract-ocr tesseract-ocr-eng
sudo apt-get install -y tesseract-ocr-vie

# ---- 2. Tạo & kích hoạt virtualenv ----
if [ ! -d "venv" ]; then
    log "Tạo môi trường ảo Python (venv)..."
    python3 -m venv venv
else
    warn "Đã có sẵn thư mục venv/, bỏ qua bước tạo mới."
fi

# shellcheck disable=SC1091
source venv/bin/activate
log "Đã kích hoạt venv."

# ---- 3. Cài thư viện Python ----
if [ -f "requirements.txt" ]; then
    log "Đang cài thư viện từ requirements.txt (có thể mất vài phút)..."
    pip install --upgrade pip
    pip install -r requirements.txt
else
    err "Không tìm thấy requirements.txt trong $PROJECT_DIR. Kiểm tra lại bạn đã copy đủ mã nguồn chưa."
    exit 1
fi

# ---- 4. Tạo file cấu hình .env ----
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        log "Đã tạo file .env từ .env.example."
    else
        warn "Không tìm thấy .env.example, tạo file .env trống."
        touch .env
    fi

    read -rp "Nhập TELEGRAM_TOKEN của bạn (lấy từ @BotFather): " TG_TOKEN
    if [ -n "$TG_TOKEN" ]; then
        if grep -q "^TELEGRAM_TOKEN=" .env; then
            sed -i "s|^TELEGRAM_TOKEN=.*|TELEGRAM_TOKEN=$TG_TOKEN|" .env
        else
            echo "TELEGRAM_TOKEN=$TG_TOKEN" >> .env
        fi
        log "Đã lưu TELEGRAM_TOKEN vào .env."
    else
        warn "Bạn chưa nhập token — nhớ mở .env và điền TELEGRAM_TOKEN trước khi chạy bot."
    fi
else
    warn "Đã có sẵn file .env, giữ nguyên không ghi đè."
fi

mkdir -p voices data logs

# ---- 5. Kiểm tra Ollama ----
if command -v ollama >/dev/null 2>&1; then
    log "Đã phát hiện Ollama trên máy."
else
    warn "Chưa thấy lệnh 'ollama'. Cài Ollama trước tại https://ollama.com rồi chạy: ollama serve"
fi

# ---- 6. Nhắc về model giọng nói Piper (tùy chọn) ----
warn "Nếu muốn dùng TTS (đọc giọng nói), tải model Piper tiếng Việt (.onnx + .onnx.json) từ"
warn "  https://huggingface.co/rhasspy/piper-voices (thư mục vi/vi_VN/) và đặt vào ./voices/"
warn "rồi khai báo qua biến PIPER_VOICE_PATHS trong .env."

# ---- 7. Hoàn tất ----
echo ""
log "Cài đặt hoàn tất! 🎉"
echo ""
echo "Các bước tiếp theo:"
echo "  1) Kiểm tra lại file .env (điền ALLOWED_USERS, ADMIN_USER_IDS nếu cần)."
echo "  2) Đảm bảo Ollama đang chạy: ollama serve"
echo "  3) Chạy thử bot:"
echo "       source venv/bin/activate"
echo "       python3 my_bot.py"
echo ""
echo "  (Tùy chọn) Chạy dashboard web:"
echo "       python -m webapp.main"
echo ""
echo "Muốn chạy bot dạng service tự khởi động cùng hệ thống, xem phần"
echo "'Chạy nền / systemd' trong README.md."
