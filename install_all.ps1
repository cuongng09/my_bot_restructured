# install_all.ps1 – One‑liner Docker installer for Windows PowerShell
# This script checks that Docker (and Docker‑Compose) are available,
# then brings up the full Ollama Telegram Bot stack via docker compose.

$ErrorActionPreference = "Stop"

function Write-ErrorMsg([string]$msg) {
    Write-Host "[ERROR] $msg" -ForegroundColor Red
}

# Verify Docker is installed
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-ErrorMsg "Docker is not installed. Install Docker Desktop from https://www.docker.com/get-started"
    exit 1
}

# Verify docker compose (v2) or docker-compose (v1) is available
$composeCmd = $null
if (docker compose version 2>$null) {
    $composeCmd = "docker compose"
} elseif (Get-Command docker-compose -ErrorAction SilentlyContinue) {
    $composeCmd = "docker-compose"
} else {
    Write-ErrorMsg "Docker Compose is not installed. Install it via Docker Desktop or `choco install docker-compose`"
    exit 1
}

Write-Host "[INFO] Starting the Docker stack..." -ForegroundColor Cyan
& $composeCmd up -d
Write-Host "[INFO] All services are up. Use '$composeCmd ps' to see them." -ForegroundColor Cyan
