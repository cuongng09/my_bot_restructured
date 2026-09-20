#!/usr/bin/env bash
# install_all.sh – One‑liner Docker installer for Linux/macOS
# This script checks that Docker (and Docker Compose) are available,
# then brings up the full Ollama Telegram Bot stack via docker compose.

set -e

# Helper to print errors in red
error() {
  printf "\033[0;31m[ERROR]\033[0m %s\n" "$1" >&2
}

# Verify Docker is installed
if ! command -v docker >/dev/null 2>&1; then
  error "Docker is not installed. Please install Docker first (https://www.docker.com/get-started)."
  exit 1
fi

# Verify docker compose (v2) or docker-compose (v1) is available
if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD="docker-compose"
else
  error "Docker Compose is not installed. Install it via Docker Desktop or "
  error "‘sudo apt-get install docker-compose’ (Linux) or ‘brew install docker-compose’ (macOS)."
  exit 1
fi

# Bring up the stack in detached mode
echo "[INFO] Starting the Docker stack..."
$COMPOSE_CMD up -d

echo "[INFO] All services are up. Use '$COMPOSE_CMD ps' to see them."
