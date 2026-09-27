#!/usr/bin/env bash
# =====================================================================
#  docker-run.sh -- Khởi chạy toàn bộ dự án qua Docker bằng 1 lệnh
#  Cách dùng:
#     chmod +x docker-run.sh && ./docker-run.sh
# =====================================================================
set -e

echo "====================================================="
echo "  Khởi động Telegram AI Bot & WebApp bằng Docker     "
echo "====================================================="

# 1. Kiểm tra Docker & Docker Compose
if ! command -v docker &> /dev/null; then
    echo "[LỖI] Docker chưa được cài đặt!"
    exit 1
fi

if docker compose version >/dev/null 2>&1; then
    COMPOSE=(docker compose)
elif command -v docker-compose &> /dev/null; then
    COMPOSE=(docker-compose)
else
    echo "[LỖI] Chưa có Docker Compose. Cài Compose plugin hoặc docker-compose."
    exit 1
fi

# 2. Tạo các thư mục cần thiết
mkdir -p data logs

# 3. Kiểm tra .env
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "[!!] Đã tạo file .env từ .env.example."
        echo "[!!] LƯU Ý: Bạn cần điền TELEGRAM_TOKEN vào file .env để bot hoạt động!"
    else
        echo "[LỖI] Không tìm thấy file .env hoặc .env.example!"
        exit 1
    fi
fi

# 4. Build và khởi chạy các container
echo "[--] Đang build image và khởi động các container..."
"${COMPOSE[@]}" up -d --build

echo ""
echo "====================================================="
echo " [THÀNH CÔNG] Toàn bộ hệ thống đã được khởi động!   "
echo "====================================================="
echo " - Web Dashboard:  http://localhost:8080"
echo " - Xem log bot:     ${COMPOSE[*]} logs -f bot"
echo " - Xem log webapp:  ${COMPOSE[*]} logs -f webapp"
echo " - Dừng hệ thống:   ${COMPOSE[*]} down"
echo "====================================================="
