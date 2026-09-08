# =====================================================================
#  uninstall.ps1 — Gỡ bỏ cài đặt Ollama Telegram Bot, WebApp & SearXNG (Windows)
#  Cách dùng (PowerShell Administrator khuyến nghị):
#     Set-ExecutionPolicy Unrestricted -Scope Process
#     .\uninstall.ps1
# =====================================================================

$ErrorActionPreference = "Continue"

function Log-OK   { param([string]$msg) Write-Host "[OK] $msg" -ForegroundColor Green }
function Log-Warn { param([string]$msg) Write-Host "[!!] $msg" -ForegroundColor Yellow }
function Log-Err  { param([string]$msg) Write-Host "[LỖI] $msg" -ForegroundColor Red }

$PROJECT_DIR = $PSScriptRoot
Set-Location $PROJECT_DIR

Write-Host "=====================================================" -ForegroundColor Red
Write-Host "             CẢNH BÁO: GỠ CÀI ĐẶT (WINDOWS)          " -ForegroundColor Red
Write-Host "=====================================================" -ForegroundColor Red
Write-Host "Thao tác này sẽ giúp bạn dọn dẹp:"
Write-Host "  1. Các dịch vụ Windows Service (NSSM nếu có)"
Write-Host "  2. WebApp Docker container"
Write-Host "  3. SearXNG Docker container"
Write-Host "  4. Môi trường ảo Python (venv)"
Write-Host "  5. Dữ liệu bot (data, logs, voices - tùy chọn)"
Write-Host "  6. File cấu hình .env (tùy chọn)"
Write-Host ""

$confirm = Read-Host "Bạn có chắc chắn muốn tiếp tục gỡ cài đặt? (y/N)"
if ($confirm -notmatch "^[Yy]$") {
    Write-Host "Đã hủy thao tác."
    exit 0
}

# ---- 1. Gỡ Windows Service NSSM nếu có ----
$uninstallNssm = Join-Path $PROJECT_DIR "scripts\uninstall_nssm_service.ps1"
if (Test-Path $uninstallNssm) {
    Log-OK "Đang kiểm tra và gỡ bỏ Windows Service (NSSM)..."
    & $uninstallNssm
}

# ---- 2. Gỡ bỏ WebApp Docker container ----
$dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
if ($dockerCmd) {
    Log-OK "Đang dừng và dọn dẹp WebApp Docker container..."
    try {
        docker compose -f docker-compose.webapp.yml down -v 2>$null
        docker rm -f telegram-bot-webapp 2>$null
        Log-OK "Đã gỡ WebApp container."
    } catch {
        Log-Warn "Không thể dừng WebApp container: $_"
    }

    # ---- 3. Gỡ bỏ SearXNG Docker container ----
    Log-OK "Đang kiểm tra và dọn dẹp SearXNG container..."
    $searxngDir = Join-Path (Split-Path $PROJECT_DIR -Parent) "searxng"
    if (-not (Test-Path $searxngDir)) {
        $searxngDir = Join-Path $PROJECT_DIR "searxng"
    }

    if (Test-Path $searxngDir) {
        Push-Location $searxngDir
        try {
            docker compose down -v 2>$null
            Log-OK "Đã dừng SearXNG container."
        } catch {
            Log-Warn "Không thể dừng SearXNG container: $_"
        } finally {
            Pop-Location
        }

        Log-OK "Đã dừng và gỡ container SearXNG (giữ nguyên thư mục cấu hình)."
    }
}

# ---- 4. Xóa môi trường ảo Python (venv) ----
if (Test-Path "venv") {
    Log-OK "Đang xóa môi trường ảo Python (venv)..."
    Remove-Item -Recurse -Force "venv" -ErrorAction SilentlyContinue
    Log-OK "Đã xóa thư mục venv\."
}

# ---- 5. Tùy chọn xóa dữ liệu (data, logs, voices - giữ lại .gitkeep) ----
$removeData = Read-Host "Bạn có muốn xóa dữ liệu bot (data, logs, voices)? (y/N)"
if ($removeData -match "^[Yy]$") {
    foreach ($folder in @("data", "logs", "voices")) {
        if (Test-Path $folder) {
            Get-ChildItem -Path $folder -Recurse -File -Force | Where-Object { $_.Name -ne ".gitkeep" } | Remove-Item -Force -ErrorAction SilentlyContinue
            Get-ChildItem -Path $folder -Recurse -Directory -Force | Where-Object { (Get-ChildItem $_.FullName -Force).Count -eq 0 } | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
    $null = New-Item -ItemType Directory -Force -Path "data\reports", "logs", "voices"
    foreach ($gk in @("data\.gitkeep", "data\reports\.gitkeep", "logs\.gitkeep", "voices\.gitkeep")) {
        if (-not (Test-Path $gk)) {
            New-Item -ItemType File -Force -Path $gk | Out-Null
        }
    }
    Log-OK "Đã dọn dẹp dữ liệu trong data, logs, voices (giữ nguyên các file .gitkeep)."
} else {
    Log-Warn "Giữ lại các thư mục dữ liệu data, logs, voices."
}

# ---- 6. Tùy chọn xóa file cấu hình .env ----
$removeEnv = Read-Host "Bạn có muốn xóa file cấu hình .env? (y/N)"
if ($removeEnv -match "^[Yy]$") {
    if (Test-Path ".env") {
        Remove-Item -Force ".env" -ErrorAction SilentlyContinue
        Log-OK "Đã xóa file .env."
    }
} else {
    Log-Warn "Giữ lại file .env."
}

Write-Host ""
Log-OK "Gỡ cài đặt trên Windows hoàn tất! 🎉"
