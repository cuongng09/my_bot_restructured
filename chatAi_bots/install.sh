#!/usr/bin/env bash
# =====================================================================
#  install.sh — Cài đặt nhanh Ollama Telegram Bot v6.2
#  Hỗ trợ: Ubuntu/Debian · Fedora/RHEL/CentOS · Arch Linux · macOS
#
#  Cách dùng:
#     chmod +x install.sh
#     ./install.sh
# =====================================================================

set -e

# ---- Màu sắc ----
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[!!]${NC} $1"; }
err()  { echo -e "${RED}[LỖI]${NC} $1"; }
info() { echo -e "${CYAN}[--]${NC} $1"; }

# =====================================================================
# 0. NHẬN DIỆN HỆ ĐIỀU HÀNH & PACKAGE MANAGER
# =====================================================================
OS="unknown"
PKG_MANAGER=""
INSTALL_CMD=""
UPDATE_CMD=""
PYTHON_PKG=""
FFMPEG_PKG="ffmpeg"
TESSERACT_PKG="tesseract"
TESSERACT_LANG_ENG=""
TESSERACT_LANG_VIE=""
VENV_PKG=""
USE_SUDO=true

detect_os() {
    local uname_out
    uname_out="$(uname -s)"

    case "$uname_out" in
        Linux)
            # Đọc /etc/os-release để phân biệt distro
            if [ -f /etc/os-release ]; then
                # shellcheck disable=SC1091
                . /etc/os-release
                case "$ID" in
                    ubuntu|debian|linuxmint|pop|kali|raspbian)
                        OS="debian"
                        PKG_MANAGER="apt"
                        UPDATE_CMD="sudo apt update"
                        INSTALL_CMD="sudo apt install -y"
                        PYTHON_PKG="python3-full python3-pip python3-venv"
                        VENV_PKG=""
                        TESSERACT_PKG="tesseract-ocr"
                        TESSERACT_LANG_ENG="tesseract-ocr-eng"
                        TESSERACT_LANG_VIE="tesseract-ocr-vie"
                        ;;
                    fedora)
                        OS="fedora"
                        PKG_MANAGER="dnf"
                        UPDATE_CMD="sudo dnf check-update || true"
                        INSTALL_CMD="sudo dnf install -y"
                        PYTHON_PKG="python3 python3-pip"
                        VENV_PKG="python3-virtualenv"
                        TESSERACT_PKG="tesseract"
                        TESSERACT_LANG_ENG="tesseract-langpack-eng"
                        TESSERACT_LANG_VIE="tesseract-langpack-vie"
                        ;;
                    rhel|centos|almalinux|rocky|ol)
                        OS="rhel"
                        PKG_MANAGER="dnf"
                        UPDATE_CMD="sudo dnf check-update || true"
                        INSTALL_CMD="sudo dnf install -y"
                        PYTHON_PKG="python3 python3-pip"
                        VENV_PKG="python3-virtualenv"
                        TESSERACT_PKG="tesseract"
                        TESSERACT_LANG_ENG="tesseract-langpack-eng"
                        TESSERACT_LANG_VIE="tesseract-langpack-vie"
                        ;;
                    arch|manjaro|endeavouros|garuda)
                        OS="arch"
                        PKG_MANAGER="pacman"
                        UPDATE_CMD="sudo pacman -Sy"
                        INSTALL_CMD="sudo pacman -S --noconfirm"
                        PYTHON_PKG="python python-pip"
                        VENV_PKG=""          # python-venv có sẵn trong python
                        TESSERACT_PKG="tesseract"
                        TESSERACT_LANG_ENG="tesseract-data-eng"
                        TESSERACT_LANG_VIE="tesseract-data-vie"
                        ;;
                    opensuse*|sles)
                        OS="opensuse"
                        PKG_MANAGER="zypper"
                        UPDATE_CMD="sudo zypper refresh"
                        INSTALL_CMD="sudo zypper install -y"
                        PYTHON_PKG="python3 python3-pip python3-virtualenv"
                        VENV_PKG=""
                        TESSERACT_PKG="tesseract-ocr"
                        TESSERACT_LANG_ENG="tesseract-ocr-traineddata-english"
                        TESSERACT_LANG_VIE="tesseract-ocr-traineddata-vietnamese"
                        ;;
                    *)
                        warn "Distro '$ID' chưa được hỗ trợ chính thức. Thử dùng apt..."
                        OS="debian"
                        PKG_MANAGER="apt"
                        UPDATE_CMD="sudo apt update"
                        INSTALL_CMD="sudo apt install -y"
                        PYTHON_PKG="python3-full python3-pip python3-venv"
                        TESSERACT_PKG="tesseract-ocr"
                        TESSERACT_LANG_ENG="tesseract-ocr-eng"
                        TESSERACT_LANG_VIE="tesseract-ocr-vie"
                        ;;
                esac
            else
                err "Không tìm thấy /etc/os-release. Không thể xác định distro."
                exit 1
            fi
            ;;
        Darwin)
            OS="macos"
            USE_SUDO=false
            if command -v brew >/dev/null 2>&1; then
                PKG_MANAGER="brew"
                UPDATE_CMD="brew update"
                INSTALL_CMD="brew install"
                PYTHON_PKG="python3"
                VENV_PKG=""
                FFMPEG_PKG="ffmpeg"
                TESSERACT_PKG="tesseract"
                TESSERACT_LANG_ENG=""          # brew cask có sẵn eng
                TESSERACT_LANG_VIE="tesseract-lang"   # chứa tất cả ngôn ngữ
            else
                err "macOS yêu cầu Homebrew. Cài tại: https://brew.sh"
                exit 1
            fi
            ;;
        MINGW*|CYGWIN*|MSYS*)
            err "Windows không được hỗ trợ bởi script này. Xem phần 'Trên Windows' trong README.md."
            exit 1
            ;;
        *)
            err "Hệ điều hành '$uname_out' không được nhận diện."
            exit 1
            ;;
    esac
}

detect_os

# In kết quả nhận diện
echo ""
info "========================================"
info " Hệ điều hành nhận diện : $(uname -s) / $OS"
info " Package manager         : $PKG_MANAGER"
info "========================================"
echo ""

# ---- Thư mục dự án ----
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"
log "Thư mục dự án: $PROJECT_DIR"

# =====================================================================
# 1. CÀI DEPENDENCY HỆ THỐNG
# =====================================================================
log "Đang cập nhật & cài dependency hệ thống..."
eval "$UPDATE_CMD"

# Packages cơ bản
PKGS=($PYTHON_PKG $FFMPEG_PKG $TESSERACT_PKG)
[ -n "$TESSERACT_LANG_ENG" ] && PKGS+=($TESSERACT_LANG_ENG)
[ -n "$TESSERACT_LANG_VIE" ] && PKGS+=($TESSERACT_LANG_VIE)
[ -n "$VENV_PKG"            ] && PKGS+=($VENV_PKG)

$INSTALL_CMD "${PKGS[@]}"

# RHEL/CentOS cần epel-release cho một số gói
if [[ "$OS" == "rhel" ]]; then
    if ! rpm -q epel-release &>/dev/null; then
        warn "Cài EPEL repository cho RHEL/CentOS..."
        sudo dnf install -y epel-release
    fi
fi

log "Đã cài xong các dependency hệ thống."

# =====================================================================
# 2. TẠO & KÍCH HOẠT VIRTUALENV
# =====================================================================
if [ ! -d "venv" ]; then
    log "Tạo môi trường ảo Python (venv)..."
    python3 -m venv venv
else
    warn "Đã có sẵn thư mục venv/, bỏ qua bước tạo mới."
fi

# shellcheck disable=SC1091
source venv/bin/activate
log "Đã kích hoạt venv."

# =====================================================================
# 3. CÀI THƯ VIỆN PYTHON
# =====================================================================
if [ -f "requirements.txt" ]; then
    log "Đang cài thư viện từ requirements.txt (có thể mất vài phút)..."
    pip install --upgrade pip
    pip install -r requirements.txt
else
    err "Không tìm thấy requirements.txt trong $PROJECT_DIR. Kiểm tra lại bạn đã copy đủ mã nguồn chưa."
    exit 1
fi

# =====================================================================
# 4. TẠO FILE CẤU HÌNH .env
# =====================================================================
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

# =====================================================================
# 5. KIỂM TRA OLLAMA
# =====================================================================
if command -v ollama >/dev/null 2>&1; then
    log "Đã phát hiện Ollama trên máy."
else
    warn "Chưa thấy lệnh 'ollama'. Cài Ollama trước tại https://ollama.com rồi chạy: ollama serve"
fi

# =====================================================================
# 6. GỢI Ý MODEL PIPER TTS
# =====================================================================
warn "Nếu muốn dùng TTS (đọc giọng nói), tải model Piper tiếng Việt (.onnx + .onnx.json) từ"
warn "  https://huggingface.co/rhasspy/piper-voices (thư mục vi/vi_VN/) và đặt vào ./voices/"
warn "rồi khai báo qua biến PIPER_VOICE_PATHS trong .env."

# =====================================================================
# 7. DOCKER & SEARXNG
# =====================================================================
echo ""
log "Kiểm tra môi trường Docker (dùng cho SearXNG & WebApp)..."
DOCKER_CMD=""
if command -v docker >/dev/null 2>&1; then
    if docker ps >/dev/null 2>&1; then
        DOCKER_CMD="docker"
    elif sudo docker ps >/dev/null 2>&1; then
        DOCKER_CMD="sudo docker"
    fi
fi

if [ -z "$DOCKER_CMD" ]; then
    warn "Chưa phát hiện Docker trên máy."
    read -rp "Bạn có muốn cài đặt Docker tự động không? (Y/n): " INSTALL_DOCKER
    INSTALL_DOCKER=${INSTALL_DOCKER:-Y}
    if [[ "$INSTALL_DOCKER" =~ ^[Yy]$ ]]; then
        log "Đang cài đặt Docker..."
        if [[ "$OS" == "macos" ]]; then
            warn "Trên macOS, vui lòng cài Docker Desktop từ: https://www.docker.com/products/docker-desktop/"
            warn "Sau khi cài xong, chạy lại script này."
        else
            curl -fsSL https://get.docker.com | sudo sh
            sudo systemctl enable --now docker
            sudo usermod -aG docker "$USER" || true
            DOCKER_CMD="sudo docker"
            log "Đã cài đặt Docker thành công."
        fi
    fi
fi

SEARXNG_STARTED=false
if [ -n "$DOCKER_CMD" ]; then
    log "Đã phát hiện Docker ($DOCKER_CMD)."
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

# =====================================================================
# 8. VOICEBOX STT QUA DOCKER (https://github.com/jamiepine/voicebox.git)
# =====================================================================
VOICEBOX_STARTED=false
if [ -n "$DOCKER_CMD" ]; then
    echo ""
    read -rp "Bạn có muốn cài đặt & khởi chạy Voicebox STT (https://github.com/jamiepine/voicebox.git) bằng Docker không? (Y/n): " RUN_VOICEBOX
    RUN_VOICEBOX=${RUN_VOICEBOX:-Y}
    if [[ "$RUN_VOICEBOX" =~ ^[Yy]$ ]]; then
        if [ -d "$PROJECT_DIR/../voicebox" ]; then
            VOICEBOX_DIR="$(cd "$PROJECT_DIR/.." && pwd)/voicebox"
        else
            VOICEBOX_DIR="$PROJECT_DIR/voicebox"
        fi

        if [ ! -d "$VOICEBOX_DIR/.git" ]; then
            log "Đang clone Voicebox từ https://github.com/jamiepine/voicebox.git..."
            git clone --depth 1 https://github.com/jamiepine/voicebox.git "$VOICEBOX_DIR"
        else
            log "Đã có sẵn thư mục Voicebox tại: $VOICEBOX_DIR"
        fi

        log "Đang build & khởi chạy Voicebox Docker container (cổng 17600)..."
        (cd "$VOICEBOX_DIR" && $DOCKER_CMD compose up -d --build)
        VOICEBOX_STARTED=true
        log "Voicebox STT đã sẵn sàng tại: http://localhost:17600"
    else
        log "Bỏ qua cài đặt Voicebox STT."
    fi
fi

# =====================================================================
# 9. WEBAPP QUA DOCKER
# =====================================================================
WEBAPP_STARTED_VIA_DOCKER=false
if [ -n "$DOCKER_CMD" ]; then
    echo ""
    read -rp "Bạn có muốn build & chạy Trạm Điều Khiển Web (WebApp) bằng Docker không? (Y/n): " RUN_DOCKER
    RUN_DOCKER=${RUN_DOCKER:-Y}
    if [[ "$RUN_DOCKER" =~ ^[Yy]$ ]]; then
        # Kiểm tra systemd service (chỉ có trên Linux)
        if [[ "$OS" != "macos" ]] && systemctl is-active --quiet telegram-bot-webapp.service 2>/dev/null; then
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

# =====================================================================
# 10. CÀI ĐẶT SYSTEMD SERVICE (chỉ Linux)
# =====================================================================
SYSTEMD_INSTALLED=false
SYSTEMD_SERVICE_NAME="telegram-bot.service"
SYSTEMD_SERVICE_FILE="/etc/systemd/system/$SYSTEMD_SERVICE_NAME"

if [[ "$OS" != "macos" ]] && command -v systemctl >/dev/null 2>&1; then
    echo ""
    read -rp "Bạn có muốn cài đặt Telegram Bot dưới dạng systemd service (tự khởi động cùng hệ thống)? (Y/n): " INSTALL_SYSTEMD
    INSTALL_SYSTEMD=${INSTALL_SYSTEMD:-Y}

    if [[ "$INSTALL_SYSTEMD" =~ ^[Yy]$ ]]; then
        log "Đang tạo file systemd service: $SYSTEMD_SERVICE_FILE"

        # Xác định đường dẫn python trong venv
        VENV_PYTHON="$PROJECT_DIR/venv/bin/python3"
        BOT_SCRIPT="$PROJECT_DIR/my_bot.py"
        SERVICE_USER="${SUDO_USER:-$USER}"

        sudo bash -c "cat > $SYSTEMD_SERVICE_FILE" <<EOF
[Unit]
Description=Telegram AI Bot
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$VENV_PYTHON $BOT_SCRIPT
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
EnvironmentFile=$PROJECT_DIR/.env

[Install]
WantedBy=multi-user.target
EOF

        log "Đã tạo file service tại: $SYSTEMD_SERVICE_FILE"

        # Reload daemon, enable & start
        sudo systemctl daemon-reload
        sudo systemctl enable "$SYSTEMD_SERVICE_NAME"
        sudo systemctl start  "$SYSTEMD_SERVICE_NAME"

        # Kiểm tra trạng thái
        sleep 2
        if systemctl is-active --quiet "$SYSTEMD_SERVICE_NAME"; then
            log "Service '$SYSTEMD_SERVICE_NAME' đang CHẠY ✅"
            SYSTEMD_INSTALLED=true
        else
            warn "Service đã được cài nhưng chưa start được — kiểm tra lại bằng:"
            warn "  sudo systemctl status $SYSTEMD_SERVICE_NAME"
            warn "  sudo journalctl -u $SYSTEMD_SERVICE_NAME -n 50"
        fi
    else
        log "Bỏ qua cài đặt systemd service."
    fi
fi

# =====================================================================
# 11. HOÀN TẤT
# =====================================================================
echo ""
log "Cài đặt hoàn tất! 🎉"
echo ""
echo "Các bước tiếp theo:"
echo "  1) Kiểm tra lại file .env (điền ALLOWED_USERS, ADMIN_USER_IDS nếu cần)."
echo "  2) Đảm bảo Ollama đang chạy: ollama serve"
if [ "$SYSTEMD_INSTALLED" = true ]; then
    echo -e "  3) Bot Telegram  : ${GREEN}● Đang chạy ngầm qua systemd${NC}"
    echo "     - Xem log        : sudo journalctl -u $SYSTEMD_SERVICE_NAME -f"
    echo "     - Dừng service   : sudo systemctl stop $SYSTEMD_SERVICE_NAME"
    echo "     - Khởi động lại  : sudo systemctl restart $SYSTEMD_SERVICE_NAME"
    echo "     - Trạng thái     : sudo systemctl status $SYSTEMD_SERVICE_NAME"
else
    echo "  3) Chạy thử bot Telegram:"
    echo "       source venv/bin/activate"
    echo "       python3 my_bot.py"
fi
echo ""
if [ "$SEARXNG_STARTED" = true ]; then
    echo -e "  4) SearXNG Web Search : ${GREEN}● Đang chạy${NC} tại http://localhost:8081"
fi
if [ "$VOICEBOX_STARTED" = true ]; then
    echo -e "  5) Voicebox STT       : ${GREEN}● Đang chạy${NC} tại http://localhost:17600"
    echo "     - Xem nhật ký (logs) : (cd $VOICEBOX_DIR && $DOCKER_CMD compose logs -f)"
    echo "     - Dừng container     : (cd $VOICEBOX_DIR && $DOCKER_CMD compose down)"
    echo "     - Khởi động lại      : (cd $VOICEBOX_DIR && $DOCKER_CMD compose restart)"
fi
echo "  6) Quản trị Trạm Điều Khiển Web (Dashboard):"
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
if [[ "$OS" != "macos" ]]; then
    if [ "$SYSTEMD_INSTALLED" = false ]; then
        echo "Muốn chạy bot dạng service tự khởi động cùng hệ thống, chạy lại install.sh"
        echo "và chọn 'Y' ở bước cài đặt systemd service."
    fi
else
    echo "Trên macOS: dùng 'launchd' hoặc chạy trực tiếp trong terminal."
fi
echo ""
