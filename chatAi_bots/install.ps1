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
    err "Script này chỉ dành cho Linux (Ubuntu/Debian). Với Windows hãy làm theo phần 'Trên Windows' trong README.md."[cite: 1]
    exit 1
fi

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"
log "Thư mục dự án: $PROJECT_DIR"[cite: 1]

# ---- 1. Cài dependency hệ thống ----
log "Đang cập nhật hệ thống và cài dependency (cần quyền sudo)..."[cite: 1]
sudo apt update
sudo apt install -y python3-full python3-pip python3-venv ffmpeg curl[cite: 1]
sudo apt install -y tesseract-ocr tesseract-ocr-eng[cite: 1]
sudo apt-get install -y tesseract-ocr-vie[cite: 1]

# ---- 2. Tạo & kích hoạt virtualenv ----
if [ ! -d "venv" ]; then
    log "Tạo môi trường ảo Python (venv)..."[cite: 1]
    python3 -m venv venv[cite: 1]
else
    warn "Đã có sẵn thư mục venv/, bỏ qua bước tạo mới."[cite: 1]
fi

# shellcheck disable=SC1091
source venv/bin/activate
log "Đã kích hoạt venv."[cite: 1]

# ---- 3. Cài thư viện Python ----
if [ -f "requirements.txt" ]; then
    log "Đang cài thư viện từ requirements.txt (có thể mất vài phút)..."[cite: 1]
    pip install --upgrade pip[cite: 1]
    pip install -r requirements.txt[cite: 1]
else
    err "Không tìm thấy requirements.txt trong $PROJECT_DIR. Kiểm tra lại bạn đã copy đủ mã nguồn chưa."[cite: 1]
    exit 1
fi

# ---- 4. Tạo file cấu hình .env ----
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env[cite: 1]
        log "Đã tạo file .env từ .env.example."[cite: 1]
    else
        warn "Không tìm thấy .env.example, tạo file .env trống."[cite: 1]
        touch .env[cite: 1]
    fi

    read -rp "Nhập TELEGRAM_TOKEN của bạn (lấy từ @BotFather): " TG_TOKEN[cite: 1]
    if [ -n "$TG_TOKEN" ]; then[cite: 1]
        if grep -q "^TELEGRAM_TOKEN=" .env; then[cite: 1]
            sed -i "s|^TELEGRAM_TOKEN=.*|TELEGRAM_TOKEN=$TG_TOKEN|" .env[cite: 1]
        else
            echo "TELEGRAM_TOKEN=$TG_TOKEN" >> .env[cite: 1]
        fi
        log "Đã lưu TELEGRAM_TOKEN vào .env."[cite: 1]
    else
        warn "Bạn chưa nhập token — nhớ mở .env và điền TELEGRAM_TOKEN trước khi chạy bot."[cite: 1]
    fi
else
    warn "Đã có sẵn file .env, giữ nguyên không ghi đè."[cite: 1]
fi

mkdir -p voices data logs[cite: 1]

# ---- 5. Kiểm tra Ollama ----
if command -v ollama >/dev/null 2>&1; then[cite: 1]
    log "Đã phát hiện Ollama trên máy."[cite: 1]
else
    warn "Chưa thấy lệnh 'ollama'. Cài Ollama trước tại https://ollama.com rồi chạy: ollama serve"[cite: 1]
fi

# ---- 6. Nhắc về model giọng nói Piper (tùy chọn) ----
warn "Nếu muốn dùng TTS (đọc giọng nói), tải model Piper tiếng Việt (.onnx + .onnx.json) từ"[cite: 1]
warn "  https://huggingface.co/rhasspy/piper-voices (thư mục vi/vi_VN/) và đặt vào ./voices/"[cite: 1]
warn "rồi khai báo qua biến PIPER_VOICE_PATHS trong .env."[cite: 1]

# ---- 7. Cài đặt & Kiểm tra SearXNG (Thêm mới) ----
log "Đang tiến hành cài đặt và khởi chạy SearXNG..."

# 7.1. Cài đặt Docker nếu chưa có
if ! command -v docker >/dev/null 2>&1; then
    log "Chưa phát hiện Docker. Đang tiến hành cài đặt Docker..."
    curl -fsSL https://get.docker.com | sudo sh
    sudo systemctl enable --now docker
    sudo usermod -aG docker "$USER" || true
else
    log "Đã phát hiện Docker trên hệ thống."
fi

# Đảm bảo daemon Docker đang chạy
sudo systemctl start docker

# 7.2. Tạo cấu trúc thư mục SearXNG
SEARXNG_DIR="$PROJECT_DIR/searxng"
mkdir -p "$SEARXNG_DIR/core-config"
cd "$SEARXNG_DIR"

# Tạo file .env cho SearXNG
if [ ! -f ".env" ]; then
    cat <<EOF > .env
SEARXNG_VERSION=latest
SEARXNG_PORT=8081
EOF
    log "Đã tạo file .env cho SearXNG (Port: 8081)."[cite: 2]
fi

# Tạo file docker-compose.yml
if [ ! -f "docker-compose.yml" ]; then
    cat <<EOF > docker-compose.yml
version: '3.7'

services:
  core:
    container_name: searxng-core
    image: searxng/searxng:\${SEARXNG_VERSION:-latest}
    ports:
      - "\${SEARXNG_PORT:-8081}:8080"
    volumes:
      - ./core-config:/etc/searxng
    environment:
      - SEARXNG_BASE_URL=http://localhost:\${SEARXNG_PORT:-8081}/
    restart: unless-stopped
EOF
    log "Đã tạo docker-compose.yml cho SearXNG."
fi

# Khởi chạy SearXNG container
log "Đang khởi chạy SearXNG via Docker Compose..."
sudo docker compose up -d[cite: 2]

# Tạo hoặc cập nhật core-config/settings.yml để bật JSON output
sleep 3
if [ ! -f "core-config/settings.yml" ]; then
    cat <<EOF > core-config/settings.yml
search:
  formats:
    - html
    - json
EOF
else
    if ! grep -q "json" core-config/settings.yml; then
        cat <<EOF >> core-config/settings.yml

search:
  formats:
    - html
    - json
EOF
    fi
fi

# Restart lại container để nhận cấu hình settings.yml
sudo docker compose restart core[cite: 2]

# 7.3. Kiểm tra server SearXNG có hoạt động tốt không
log "Đang kiểm tra trạng thái hoạt động của SearXNG server..."
sleep 5

HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8081 || true)
if [ "$HTTP_STATUS" -eq 200 ] || [ "$HTTP_STATUS" -eq 302 ]; then
    log "SearXNG Web Interface đang phản hồi tốt (HTTP Status: $HTTP_STATUS)."
else
    warn "SearXNG phản hồi HTTP Code $HTTP_STATUS. Có thể container đang trong quá trình khởi động."
fi

# Kiểm tra JSON API
JSON_CHECK=$(curl -s "http://localhost:8081/search?q=test&format=json" || true)[cite: 2]
if echo "$JSON_CHECK" | grep -q "results"; then
    log "Kiểm tra SearXNG JSON API thành công! Server hoạt động bình thường."
else
    warn "Chưa thể lấy dữ liệu JSON API từ SearXNG. Hãy kiểm tra lại bằng lệnh: docker compose logs core"[cite: 2]
fi

cd "$PROJECT_DIR"

# ---- 8. Hoàn tất ----
echo ""
log "Cài đặt hoàn tất! 🎉"[cite: 1]
echo ""
echo "Các bước tiếp theo:"[cite: 1]
echo "  1) Kiểm tra lại file .env (điền ALLOWED_USERS, ADMIN_USER_IDS nếu cần)."[cite: 1]
echo "  2) Đảm bảo Ollama đang chạy: ollama serve"[cite: 1]
echo "  3) Chạy thử bot:"[cite: 1]
echo "       source venv/bin/activate"[cite: 1]
echo "       python3 my_bot.py"[cite: 1]
echo ""
echo "  (Tùy chọn) Chạy dashboard web:"[cite: 1]
echo "       python -m webapp.main"[cite: 1]
echo ""
echo "Muốn chạy bot dạng service tự khởi động cùng hệ thống, xem phần"[cite: 1]
echo "'Chạy nền / systemd' trong README.md."[cite: 1]