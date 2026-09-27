#!/usr/bin/env bash
set -Eeuo pipefail

# The installer is intentionally anchored at the repository root so it is safe
# to invoke as ./scripts/install.sh from any working directory.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -f "$ROOT/pyproject.toml" ]]; then
  echo "Không tìm thấy pyproject.toml tại $ROOT" >&2
  exit 1
fi

log() { printf '[my-bot] %s\n' "$*"; }
confirm() {
  local answer
  read -r -p "$1 [Y/n] " answer || true
  [[ -z "$answer" || "$answer" =~ ^[Yy]$ ]]
}

if [[ "$(uname -s)" == "Darwin" ]] && ! command -v brew >/dev/null 2>&1; then
  echo "macOS yêu cầu Homebrew để cài Python: https://brew.sh" >&2
  exit 1
fi

if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y python3 python3-pip python3-venv
elif command -v dnf >/dev/null 2>&1; then
  sudo dnf install -y python3 python3-pip python3-virtualenv
elif command -v pacman >/dev/null 2>&1; then
  sudo pacman -Sy --needed --noconfirm python python-pip
elif command -v brew >/dev/null 2>&1; then
  brew install python 2>/dev/null || true
else
  log "Không nhận diện package manager; hãy cài Python 3.11/3.12 thủ công."
fi

PYTHON_BIN="${PYTHON_BIN:-python3}"
if [[ ! -d "$ROOT/.venv" ]]; then
  "$PYTHON_BIN" -m venv "$ROOT/.venv"
fi
"$ROOT/.venv/bin/python" -m pip install --upgrade pip
"$ROOT/.venv/bin/python" -m pip install -e ".[dev]"

if [[ ! -f "$ROOT/.env" ]]; then
  cp "$ROOT/.env.example" "$ROOT/.env"
  read -r -p "TELEGRAM_TOKEN (Enter để điền sau): " token || true
  if [[ -n "$token" ]]; then
    sed -i.bak "s|^TELEGRAM_TOKEN=.*|TELEGRAM_TOKEN=$token|" "$ROOT/.env"
    rm -f "$ROOT/.env.bak"
  fi
fi
mkdir -p "$ROOT/data" "$ROOT/logs"

if ! command -v ollama >/dev/null 2>&1; then
  log "Ollama chưa được cài; tải tại https://ollama.com (installer không thất bại vì bước này)."
fi

if confirm "Bật SearXNG bằng Docker Compose?"; then
  if docker compose version >/dev/null 2>&1; then
    docker compose up -d searxng
  elif command -v docker-compose >/dev/null 2>&1; then
    docker-compose up -d searxng
  else
    log "Docker Compose chưa có; bỏ qua SearXNG. Cài Compose rồi chạy lại installer."
  fi
fi

if [[ "$(uname -s)" == "Linux" ]] && command -v systemctl >/dev/null 2>&1 && confirm "Cài systemd service my-bot?"; then
  sudo install -m 0644 "$ROOT/scripts/systemd/my_bot.service" /etc/systemd/system/my_bot.service
  sudo sed -i "s|/opt/my_bot|$ROOT|g; s|User=%I|User=${SUDO_USER:-$USER}|" /etc/systemd/system/my_bot.service
  sudo systemctl daemon-reload
  sudo systemctl enable --now my_bot.service
  log "Logs: journalctl -u my_bot.service -f"
fi

log "Cài đặt hoàn tất tại $ROOT"
log "Chạy bot: $ROOT/.venv/bin/python -m my_bot"
log "Chạy webapp: $ROOT/.venv/bin/my-bot-web"
