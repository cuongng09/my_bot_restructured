#!/usr/bin/env bash
# =====================================================================
#  uninstall.sh — Script gỡ bỏ toàn bộ cài đặt (Ollama Bot + SearXNG)
#
#  Cách dùng:
#     chmod +x uninstall.sh
#     ./uninstall.sh
# =====================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[!!]${NC} $1"; }
err()  { echo -e "${RED}[LỖI]${NC} $1"; }

if [[ "$(uname)" != "Linux" ]]; then
    err "Script này chỉ dành cho Linux (Ubuntu/Debian)."
    exit 1
fi

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo -e "${RED}=====================================================${NC}"
echo -e "${RED}             CẢNH BÁO: CẢNH BÁO GỠ CÀI ĐẶT             ${NC}"
echo -e "${RED}=====================================================${NC}"
echo "Thao tác này sẽ gỡ bỏ:"
echo "  1. Dừng & Xóa SearXNG Docker container, volumes, file cấu hình"
echo "  2. Môi trường ảo Python (venv)"
echo "  3. Các thư mục dữ liệu (data, logs, voices - tùy chọn)"
echo "  4. File cấu hình .env (tùy chọn)"
echo ""

read -rp "Bạn có chắc chắn muốn gỡ bỏ hoàn toàn? (y/N): " CONFIRM
if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
    echo "Đã hủy thao tác."
    exit 0
fi

# ---- 1. Gỡ bỏ SearXNG Docker Container ----
log "1. Đang dừng và gỡ bỏ SearXNG Docker container..."
if [ -d "$PROJECT_DIR/searxng" ]; then
    cd "$PROJECT_DIR/searxng"
    if command -v docker >/dev/null 2>&1; then
        sudo docker compose down -v || true
    fi
    cd "$PROJECT_DIR"
    rm -rf "$PROJECT_DIR/searxng"
    log "Đã xóa thư mục và container SearXNG."
else
    warn "Không tìm thấy thư mục searxng/, bỏ qua."
fi

# ---- 2. Xóa môi trường ảo Python (venv) ----
log "2. Đang xóa môi trường ảo Python (venv)..."
if [ -d "venv" ]; then
    rm -rf venv
    log "Đã xóa thư mục venv/."
else
    warn "Không tìm thấy thư mục venv/, bỏ qua."
fi

# ---- 3. Hỏi xóa các thư mục data, logs, voices ----
read -rp "Bạn có muốn xóa dữ liệu bot (data, logs, voices)? (y/N): " REMOVE_DATA
if [[ "$REMOVE_DATA" == "y" || "$REMOVE_DATA" == "Y" ]]; then
    rm -rf data logs voices
    log "Đã xóa các thư mục data, logs, voices."
else
    warn "Giữ lại các thư mục dữ liệu data, logs, voices."
fi

# ---- 4. Hỏi xóa file cấu hình .env ----
read -rp "Bạn có muốn xóa file cấu hình .env? (y/N): " REMOVE_ENV
if [[ "$REMOVE_ENV" == "y" || "$REMOVE_ENV" == "Y" ]]; then
    rm -f .env
    log "Đã xóa file .env."
else
    warn "Giữ lại file .env."
fi

echo ""
log "Gỡ cài đặt hoàn tất! 🎉"
