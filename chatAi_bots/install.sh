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

# ---- 7. Cài đặt Docker & SearXNG (Tìm kiếm Web RAG) ----
echo ""
log "Kiểm tra môi trường Docker (dùng cho SearXNG & WebApp)..."
DOCKER_CMD=""
if command -v docker >/dev/null 2>&1; then
    if docker ps >/dev/null 2>&1; then
        DOCKER_CMD="docker"
    elif sudo -n docker ps >/dev/null 2>&1 || sudo docker ps >/dev/null 2>&1; then
        DOCKER_CMD="sudo docker"
    fi
fi

if [ -z "$DOCKER_CMD" ]; then
    warn "Chưa phát hiện Docker trên máy."
    read -rp "Bạn có muốn cài đặt Docker tự động không? (Y/n): " INSTALL_DOCKER
    INSTALL_DOCKER=${INSTALL_DOCKER:-Y}
    if [[ "$INSTALL_DOCKER" =~ ^[Yy]$ ]]; then
        log "Đang cài đặt Docker..."
        curl -fsSL https://get.docker.com | sudo sh
        sudo systemctl enable --now docker
        sudo usermod -aG docker "$USER" || true
        DOCKER_CMD="sudo docker"
        log "Đã cài đặt Docker thành công."
    fi
fi

SEARXNG_STARTED=false
if [ -n "$DOCKER_CMD" ]; then
    log "Đã phát hiện Docker trên máy ($DOCKER_CMD)."
    read -rp "Bạn có muốn cài đặt & chạy SearXNG (RAG tìm kiếm web tự host) bằng Docker không? (Y/n): " RUN_SEARXNG
    RUN_SEARXNG=${RUN_SEARXNG:-Y}
    if [[ "$RUN_SEARXNG" =~ ^[Yy]$ ]]; then
        if [ -d "$PROJECT_DIR/../searxng" ]; then
            SEARXNG_DIR="$(cd "$PROJECT_DIR/.." && pwd)/searxng"
        else
            SEARXNG_DIR="$PROJECT_DIR/searxng"
        fi
        mkdir -p "$SEARXNG_DIR/core-config"

        if [ ! -f "$SEARXNG_DIR/.env" ]; then
            cat <<EOF > "$SEARXNG_DIR/.env"
SEARXNG_VERSION=latest
SEARXNG_PORT=8081
EOF
            log "Đã tạo file .env cho SearXNG (Port: 8081)."
        fi

        if [ ! -f "$SEARXNG_DIR/docker-compose.yml" ]; then
            cat <<EOF > "$SEARXNG_DIR/docker-compose.yml"
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

        if [ ! -f "$SEARXNG_DIR/core-config/settings.yml" ]; then
            cat <<EOF > "$SEARXNG_DIR/core-config/settings.yml"
use_default_settings: true
server:
  secret_key: "$(openssl rand -hex 16 2>/dev/null || echo '4uVZ7CVCjzuOg5spOLyeG2Lpf9b97aYF')"
  image_proxy: true
search:
  formats:
    - html
    - json
EOF
            log "Đã tạo file cấu hình settings.yml cho SearXNG."
        else
            if ! grep -q "json" "$SEARXNG_DIR/core-config/settings.yml"; then
                cat <<EOF >> "$SEARXNG_DIR/core-config/settings.yml"

search:
  formats:
    - html
    - json
EOF
                log "Đã bật định dạng json trong settings.yml của SearXNG."
            fi
        fi

        log "Đang khởi chạy SearXNG container..."
        (cd "$SEARXNG_DIR" && $DOCKER_CMD compose up -d)
        SEARXNG_STARTED=true
        log "SearXNG đã sẵn sàng tại: http://localhost:8081"
    else
        log "Bỏ qua cài đặt SearXNG."
    fi
fi

# ---- 8. Tùy chọn cài đặt & khởi chạy WebApp qua Docker ----
WEBAPP_STARTED_VIA_DOCKER=false
if [ -n "$DOCKER_CMD" ]; then
    echo ""
    read -rp "Bạn có muốn build & chạy Trạm Điều Khiển Web (WebApp) bằng Docker không? (Y/n): " RUN_DOCKER
    RUN_DOCKER=${RUN_DOCKER:-Y}
    if [[ "$RUN_DOCKER" =~ ^[Yy]$ ]]; then
        if systemctl is-active --quiet telegram-bot-webapp.service 2>/dev/null; then
            warn "Phát hiện service systemd 'telegram-bot-webapp.service' đang chạy."
            read -rp "Bạn có muốn dừng service systemd này để chuyển sang chạy bằng Docker không? (y/N): " STOP_SYSTEMD
            if [[ "$STOP_SYSTEMD" =~ ^[Yy]$ ]]; then
                sudo systemctl stop telegram-bot-webapp.service 2>/dev/null || true
                sudo systemctl disable telegram-bot-webapp.service 2>/dev/null || true
                log "Đã dừng và vô hiệu hóa systemd service telegram-bot-webapp."
            fi
        fi
        log "Đang build Docker image cho WebApp..."
        if $DOCKER_CMD compose version >/dev/null 2>&1; then
            $DOCKER_CMD compose -f docker-compose.webapp.yml build webapp
            log "Đang khởi động container WebApp..."
            $DOCKER_CMD compose -f docker-compose.webapp.yml up -d webapp
            WEBAPP_STARTED_VIA_DOCKER=true
        else
            $DOCKER_CMD build -t telegram-bot-webapp -f Dockerfile.webapp .
            $DOCKER_CMD run -d --name telegram-bot-webapp --restart unless-stopped \
                --network host \
                -v "$PROJECT_DIR/data:/app/data:ro" \
                -v "$PROJECT_DIR/logs:/app/logs:ro" \
                -v "$PROJECT_DIR/.env:/app/.env:ro" \
                telegram-bot-webapp
            WEBAPP_STARTED_VIA_DOCKER=true
        fi
        log "WebApp container đã được khởi chạy thành công! 🎉"
    else
        log "Bỏ qua khởi chạy WebApp Docker."
    fi
else
    warn "Chưa có Docker — Bạn có thể chạy WebApp trực tiếp qua Python: python -m webapp.main"
fi

# ---- 9. Hoàn tất ----
echo ""
log "Cài đặt hoàn tất! 🎉"
echo ""
echo "Các bước tiếp theo:"
echo "  1) Kiểm tra lại file .env (điền ALLOWED_USERS, ADMIN_USER_IDS nếu cần)."
echo "  2) Đảm bảo Ollama đang chạy: ollama serve"
echo "  3) Chạy thử bot Telegram:"
echo "       source venv/bin/activate"
echo "       python3 my_bot.py"
echo ""
if [ "$SEARXNG_STARTED" = true ]; then
    echo -e "  4) SearXNG Web Search : ${GREEN}● Đang chạy${NC} tại http://localhost:8081"
fi
echo "  5) Quản trị Trạm Điều Khiển Web (Dashboard):"
if [ "$WEBAPP_STARTED_VIA_DOCKER" = true ]; then
    echo -e "     ${GREEN}●${NC} WebApp ĐANG CHẠY ngầm qua Docker tại: http://localhost:8080"
    echo "     - Xem nhật ký (logs) : $DOCKER_CMD compose -f docker-compose.webapp.yml logs -f webapp"
    echo "     - Dừng WebApp        : $DOCKER_CMD compose -f docker-compose.webapp.yml down"
    echo "     - Khởi động lại      : $DOCKER_CMD compose -f docker-compose.webapp.yml restart webapp"
else
    echo "     - Cách 1 (Khuyên dùng - Docker):"
    echo "         docker compose -f docker-compose.webapp.yml up -d"
    echo "     - Cách 2 (Trực tiếp qua Python):"
    echo "         source venv/bin/activate"
    echo "         python -m webapp.main"
fi
echo ""
echo "Muốn chạy bot dạng service tự khởi động cùng hệ thống, xem phần"
echo "'Chạy nền / systemd' trong README.md."
