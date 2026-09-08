#!/usr/bin/env bash
# =====================================================================
#  uninstall.sh — Script gỡ bỏ toàn bộ cài đặt (Ollama Bot + SearXNG)
#  Hỗ trợ: Ubuntu/Debian · Fedora/RHEL/CentOS · Arch Linux · macOS
#
#  Cách dùng:
#     chmod +x uninstall.sh
#     ./uninstall.sh
# =====================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[!!]${NC} $1"; }
err()  { echo -e "${RED}[LỖI]${NC} $1"; }
info() { echo -e "${CYAN}[--]${NC} $1"; }

# =====================================================================
# 0. NHẬN DIỆN HỆ ĐIỀU HÀNH
# =====================================================================
OS="unknown"

detect_os() {
    local uname_out
    uname_out="$(uname -s)"

    case "$uname_out" in
        Linux)
            if [ -f /etc/os-release ]; then
                # shellcheck disable=SC1091
                . /etc/os-release
                case "$ID" in
                    ubuntu|debian|linuxmint|pop|kali|raspbian) OS="debian"   ;;
                    fedora)                                     OS="fedora"   ;;
                    rhel|centos|almalinux|rocky|ol)            OS="rhel"     ;;
                    arch|manjaro|endeavouros|garuda)            OS="arch"     ;;
                    opensuse*|sles)                             OS="opensuse" ;;
                    *)
                        warn "Distro '$ID' chưa được hỗ trợ chính thức — tiếp tục với cấu hình mặc định."
                        OS="linux_generic"
                        ;;
                esac
            else
                OS="linux_generic"
            fi
            ;;
        Darwin)
            OS="macos"
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

echo ""
info "========================================"
info " Hệ điều hành nhận diện : $(uname -s) / $OS"
info "========================================"
echo ""

# ---- Thư mục dự án ----
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# ---- Tự động xác định lệnh Docker ----
DOCKER_CMD=""
if command -v docker >/dev/null 2>&1; then
    if docker ps >/dev/null 2>&1; then
        DOCKER_CMD="docker"
    elif sudo docker ps >/dev/null 2>&1; then
        DOCKER_CMD="sudo docker"
    fi
fi

# =====================================================================
# CẢNH BÁO
# =====================================================================
echo -e "${RED}=====================================================${NC}"
echo -e "${RED}         CẢNH BÁO: THAO TÁC GỠ CÀI ĐẶT             ${NC}"
echo -e "${RED}=====================================================${NC}"
echo "Thao tác này sẽ gỡ bỏ:"
echo "  1. Dừng & Gỡ container SearXNG & WebApp Docker (giữ nguyên thư mục cấu hình)"
echo "  2. Dừng, vô hiệu hóa & xóa systemd service telegram-bot (nếu có)"
echo "  3. Môi trường ảo Python (venv)"
echo "  4. Các thư mục dữ liệu (data, logs, voices — tùy chọn)"
echo "  5. File cấu hình .env (tùy chọn)"
echo ""

read -rp "Bạn có chắc chắn muốn gỡ bỏ hoàn toàn? (y/N): " CONFIRM
if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
    echo "Đã hủy thao tác."
    exit 0
fi

# =====================================================================
# 1. GỠ BỎ SEARXNG DOCKER CONTAINER
# =====================================================================
log "1. Đang dừng và gỡ bỏ SearXNG Docker container..."
SEARXNG_PATH=""
if [ -d "$PROJECT_DIR/searxng" ]; then
    SEARXNG_PATH="$PROJECT_DIR/searxng"
elif [ -d "$PROJECT_DIR/../searxng" ]; then
    SEARXNG_PATH="$(cd "$PROJECT_DIR/.." && pwd)/searxng"
fi

if [ -n "$SEARXNG_PATH" ] && [ -n "$DOCKER_CMD" ]; then
    (cd "$SEARXNG_PATH" && $DOCKER_CMD compose down -v 2>/dev/null || true)
    log "Đã dừng và gỡ container SearXNG (giữ nguyên thư mục cấu hình)."
elif [ -z "$DOCKER_CMD" ]; then
    warn "Không tìm thấy Docker — bỏ qua bước dừng SearXNG container."
else
    warn "Không tìm thấy thư mục searxng/, bỏ qua."
fi

# =====================================================================
# 1.1 GỠ BỎ WEBAPP DOCKER CONTAINER
# =====================================================================
log "1.1 Đang dừng và gỡ bỏ WebApp Docker container..."
if [ -n "$DOCKER_CMD" ]; then
    $DOCKER_CMD compose -f docker-compose.webapp.yml down -v 2>/dev/null || true
    $DOCKER_CMD rm -f telegram-bot-webapp 2>/dev/null || true
    log "Đã dọn dẹp WebApp Docker container."
else
    warn "Không có Docker — bỏ qua bước dừng WebApp container."
fi

# =====================================================================
# 1.2 GỠ BỎ SYSTEMD SERVICE (chỉ Linux)
# =====================================================================
if [[ "$OS" != "macos" ]] && command -v systemctl >/dev/null 2>&1; then
    log "1.2 Đang kiểm tra và gỡ bỏ systemd service..."

    # Danh sách các service cần kiểm tra và xóa
    SERVICES=("telegram-bot.service" "telegram-bot-webapp.service")
    for SVC in "${SERVICES[@]}"; do
        SVC_FILE="/etc/systemd/system/$SVC"

        # Dừng nếu đang chạy
        if systemctl is-active --quiet "$SVC" 2>/dev/null; then
            warn "Đang dừng service '$SVC'..."
            sudo systemctl stop "$SVC" 2>/dev/null || true
            log "Đã dừng '$SVC'."
        fi

        # Disable nếu được enable
        if systemctl is-enabled --quiet "$SVC" 2>/dev/null; then
            sudo systemctl disable "$SVC" 2>/dev/null || true
            log "Đã vô hiệu hóa '$SVC'."
        fi

        # Xóa file .service nếu tồn tại
        if [ -f "$SVC_FILE" ]; then
            read -rp "Bạn có muốn xóa file service '$SVC_FILE'? (Y/n): " RM_SVC
            RM_SVC=${RM_SVC:-Y}
            if [[ "$RM_SVC" =~ ^[Yy]$ ]]; then
                sudo rm -f "$SVC_FILE"
                log "Đã xóa file: $SVC_FILE"
            else
                warn "Giữ lại file: $SVC_FILE"
            fi
        fi
    done

    # Reload daemon để đồng bộ lại sau khi xóa file
    sudo systemctl daemon-reload
    sudo systemctl reset-failed 2>/dev/null || true
    log "Đã reload systemd daemon."
else
    info "macOS hoặc systemd không khả dụng — bỏ qua bước gỡ systemd service."
fi

# =====================================================================
# 2. XÓA MÔI TRƯỜNG ẢO PYTHON (VENV)
# =====================================================================
log "2. Đang xóa môi trường ảo Python (venv)..."
if [ -d "venv" ]; then
    rm -rf venv
    log "Đã xóa thư mục venv/."
else
    warn "Không tìm thấy thư mục venv/, bỏ qua."
fi

# =====================================================================
# 3. HỎI XÓA data, logs, voices
# =====================================================================
read -rp "Bạn có muốn xóa dữ liệu bot (data, logs, voices)? (y/N): " REMOVE_DATA
if [[ "$REMOVE_DATA" == "y" || "$REMOVE_DATA" == "Y" ]]; then
    for dir in data logs voices; do
        if [ -d "$dir" ]; then
            find "$dir" -type f ! -name ".gitkeep" -delete 2>/dev/null || true
            find "$dir" -mindepth 1 -type d -empty -delete 2>/dev/null || true
        fi
    done
    mkdir -p data/reports logs voices
    touch data/.gitkeep data/reports/.gitkeep logs/.gitkeep voices/.gitkeep 2>/dev/null || true
    log "Đã dọn dẹp dữ liệu trong data, logs, voices (giữ nguyên các file .gitkeep)."
else
    warn "Giữ lại các thư mục dữ liệu data, logs, voices."
fi

# =====================================================================
# 4. HỎI XÓA FILE .env
# =====================================================================
read -rp "Bạn có muốn xóa file cấu hình .env? (y/N): " REMOVE_ENV
if [[ "$REMOVE_ENV" == "y" || "$REMOVE_ENV" == "Y" ]]; then
    rm -f .env
    log "Đã xóa file .env."
else
    warn "Giữ lại file .env."
fi

echo ""
log "Gỡ cài đặt hoàn tất! 🎉"