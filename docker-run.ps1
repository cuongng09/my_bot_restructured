# =====================================================================
#  docker-run.ps1 -- Khởi chạy toàn bộ dự án qua Docker bằng 1 lệnh
#  Cách dùng:
#     .\docker-run.ps1
# =====================================================================
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "  Khoi dong Telegram AI Bot & WebApp bang Docker     " -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

# 1. Kiem tra Docker & Docker Compose
$dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
if (-not $dockerCmd) {
    Write-Host "[LOI] Docker chua duoc cai dat hoac chua duoc them vao PATH!" -ForegroundColor Red
    Write-Host "Vui long cai Docker Desktop tu: https://www.docker.com/products/docker-desktop/" -ForegroundColor Yellow
    exit 1
}

# 2. Tu dong tao cac thu muc can thiet truoc khi mount volume
$folders = @("data", "logs", "fonts", "voices")
foreach ($folder in $folders) {
    if (-not (Test-Path $folder)) {
        New-Item -ItemType Directory -Path $folder -Force | Out-Null
        Write-Host "[OK] Da tao thu muc: $folder" -ForegroundColor Green
    }
}

# 3. Kiem tra file .env
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "[!!] Da khoi tao file .env tu .env.example." -ForegroundColor Yellow
        Write-Host "[!!] LUU Y: Ban can dien TELEGRAM_TOKEN vao file .env de bot hoat dong!" -ForegroundColor Red
    } else {
        Write-Host "[LOI] Khong tim thay .env hoac .env.example!" -ForegroundColor Red
        exit 1
    }
}

# 4. Kiem tra TELEGRAM_TOKEN trong .env
$envContent = Get-Content ".env" -Raw
if ($envContent -match "TELEGRAM_TOKEN=\s*(\r?\n|$)") {
    Write-Host "[CANH BAO] TELEGRAM_TOKEN trong file .env dang de trong!" -ForegroundColor Yellow
    Write-Host "           Bot se khong the ket noi Telegram cho toi khi ban dien token." -ForegroundColor Yellow
}

# 5. Build va khoi dong container
Write-Host "[--] Dang build image va khoi dong cac container..." -ForegroundColor Cyan
docker compose up -d --build

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "=====================================================" -ForegroundColor Green
    Write-Host " [THANH CONG] Toan bo he thong da duoc khoi dong!   " -ForegroundColor Green
    Write-Host "=====================================================" -ForegroundColor Green
    Write-Host " - Web Dashboard:  http://localhost:8080" -ForegroundColor Cyan
    Write-Host " - Xem log bot:     docker compose logs -f bot" -ForegroundColor White
    Write-Host " - Xem log webapp:  docker compose logs -f webapp" -ForegroundColor White
    Write-Host " - Dung he thong:   docker compose down" -ForegroundColor White
    Write-Host "=====================================================" -ForegroundColor Green
} else {
    Write-Host "[LOI] Khoi dong Docker compose that bai!" -ForegroundColor Red
}
