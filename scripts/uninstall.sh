#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

read -r -p "Gỡ dịch vụ/container của my_bot? Dữ liệu sẽ được giữ lại. [y/N] " confirm || true
[[ "$confirm" =~ ^[Yy]$ ]] || { echo "Đã hủy."; exit 0; }

if command -v systemctl >/dev/null 2>&1; then
  for service in my_bot.service my-bot.service telegram-bot.service telegram-bot-webapp.service; do
    sudo systemctl disable --now "$service" 2>/dev/null || true
    sudo rm -f "/etc/systemd/system/$service"
  done
  sudo systemctl daemon-reload
fi

if command -v docker >/dev/null 2>&1; then
  docker compose down 2>/dev/null || true
fi

read -r -p "Xóa môi trường .venv? [y/N] " remove_venv || true
if [[ "$remove_venv" =~ ^[Yy]$ ]]; then
  rm -rf "$ROOT/.venv"
fi

read -r -p "Xóa .env, data/ và logs/? Không thể hoàn tác. [y/N] " remove_data || true
if [[ "$remove_data" =~ ^[Yy]$ ]]; then
  rm -f "$ROOT/.env"
  rm -rf "$ROOT/data" "$ROOT/logs"
fi

echo "Đã gỡ các thành phần được chọn; mã nguồn và cấu hình searxng/ vẫn được giữ lại."
