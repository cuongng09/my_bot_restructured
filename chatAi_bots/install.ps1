# =====================================================================
#  install.ps1 — Cài đặt nhanh Ollama Telegram Bot v6.2 trên Windows
#  Cách dùng (PowerShell Administrator khuyến nghị):
#     Set-ExecutionPolicy Unrestricted -Scope Process
#     .\install.ps1
# =====================================================================

$ErrorActionPreference = "Stop"

function Log-OK   { param([string]$msg) Write-Host "[OK] $msg" -ForegroundColor Green }
function Log-Warn { param([string]$msg) Write-Host "[!!] $msg" -ForegroundColor Yellow }
function Log-Err  { param([string]$msg) Write-Host "[LỖI] $msg" -ForegroundColor Red }

Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "  Cài đặt Ollama Telegram Bot & Web Dashboard (Windows)" -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

$PROJECT_DIR = $PSScriptRoot
Set-Location $PROJECT_DIR
Log-OK "Thư mục dự án: $PROJECT_DIR"

# ---- 1. Kiểm tra Python ----
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Log-Err "Không tìm thấy Python trên hệ thống!"
    Write-Host "Vui lòng cài đặt Python 3.11 hoặc 3.12 từ https://www.python.org (nhớ tích chọn 'Add Python to PATH')."
    exit 1
}
Log-OK "Đã phát hiện Python: $($pythonCmd.Source)"

# ---- 2. Tạo & kích hoạt virtualenv ----
if (-not (Test-Path "venv")) {
    Log-OK "Tạo môi trường ảo Python (venv)..."
    python -m venv venv
} else {
    Log-Warn "Đã có sẵn thư mục venv\, bỏ qua bước tạo mới."
}

$venvPython = Join-Path $PROJECT_DIR "venv\Scripts\python.exe"
$venvPip = Join-Path $PROJECT_DIR "venv\Scripts\pip.exe"

# ---- 3. Cài thư viện Python ----
if (Test-Path "requirements.txt") {
    Log-OK "Đang nâng cấp pip và cài đặt dependencies từ requirements.txt..."
    & $venvPython -m pip install --upgrade pip
    & $venvPip install -r requirements.txt
    Log-OK "Cài đặt thư viện Python thành công."
} else {
    Log-Err "Không tìm thấy requirements.txt trong $PROJECT_DIR."
    exit 1
}

# ---- 4. Tạo file cấu hình .env ----
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Log-OK "Đã tạo file .env từ .env.example."
    } else {
        New-Item -ItemType File -Path ".env" | Out-Null
        Log-Warn "Không tìm thấy .env.example, tạo file .env trống."
    }

    $tgToken = Read-Host "Nhập TELEGRAM_TOKEN của bạn (lấy từ @BotFather)"
    if ($tgToken) {
        $envContent = Get-Content ".env" -Raw
        if ($envContent -match "^TELEGRAM_TOKEN=") {
            $envContent = $envContent -replace "^TELEGRAM_TOKEN=.*", "TELEGRAM_TOKEN=$tgToken"
            Set-Content ".env" $envContent
        } else {
            Add-Content ".env" "TELEGRAM_TOKEN=$tgToken"
        }
        Log-OK "Đã lưu TELEGRAM_TOKEN vào .env."
    } else {
        Log-Warn "Bạn chưa nhập token — nhớ mở .env và điền TELEGRAM_TOKEN trước khi chạy bot."
    }
} else {
    Log-Warn "Đã có sẵn file .env, giữ nguyên không ghi đè."
}

# Tạo các thư mục dữ liệu
$null = New-Item -ItemType Directory -Force -Path "voices", "data", "logs"

# ---- 5. Kiểm tra Ollama ----
$ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue
if ($ollamaCmd) {
    Log-OK "Đã phát hiện Ollama trên máy."
} else {
    Log-Warn "Chưa thấy lệnh 'ollama'. Hãy tải và cài đặt Ollama từ https://ollama.com rồi chạy: ollama serve"
}

# ---- 6. Nhắc nhở về Voice Piper & Tesseract OCR ----
Log-Warn "Nếu muốn dùng TTS (đọc giọng nói), tải model Piper tiếng Việt (.onnx + .onnx.json) từ"
Log-Warn "  https://huggingface.co/rhasspy/piper-voices (thư mục vi/vi_VN/) và đặt vào .\voices\"
Log-Warn "Nếu muốn dùng OCR trích xuất chữ trong ảnh, hãy cài Tesseract OCR Windows và đặt đường dẫn trong .env:"
Log-Warn "  TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe"

# ---- 7. Cài đặt Docker, SearXNG & WebApp ----
$dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
$searxngStarted = $false
$webappStarted = $false

if ($dockerCmd) {
    Log-OK "Đã phát hiện Docker Desktop trên hệ thống."
    
    # 7.1 Cài đặt SearXNG
    $installSearxng = Read-Host "Bạn có muốn cài đặt & khởi chạy SearXNG (Web Search RAG) bằng Docker không? (Y/n)"
    if ([string]::IsNullOrWhiteSpace($installSearxng) -or $installSearxng -match "^[Yy]$") {
        $searxngDir = Join-Path (Split-Path $PROJECT_DIR -Parent) "searxng"
        if (-not (Test-Path $searxngDir)) {
            $searxngDir = Join-Path $PROJECT_DIR "searxng"
        }
        $null = New-Item -ItemType Directory -Force -Path (Join-Path $searxngDir "core-config")

        $searxngEnv = Join-Path $searxngDir ".env"
        if (-not (Test-Path $searxngEnv)) {
            @"
SEARXNG_VERSION=latest
SEARXNG_PORT=8081
"@ | Set-Content $searxngEnv
            Log-OK "Đã tạo file .env cho SearXNG (Port 8081)."
        }

        $searxngCompose = Join-Path $searxngDir "docker-compose.yml"
        if (-not (Test-Path $searxngCompose)) {
            @"
services:
  core:
    container_name: searxng-core
    image: searxng/searxng:`${SEARXNG_VERSION:-latest}
    ports:
      - "`${SEARXNG_PORT:-8081}:8080"
    volumes:
      - ./core-config:/etc/searxng
    environment:
      - SEARXNG_BASE_URL=http://localhost:`${SEARXNG_PORT:-8081}/
    restart: unless-stopped
"@ | Set-Content $searxngCompose
            Log-OK "Đã tạo docker-compose.yml cho SearXNG."
        }

        $searxngSettings = Join-Path $searxngDir "core-config\settings.yml"
        if (-not (Test-Path $searxngSettings)) {
            @"
use_default_settings: true
server:
  secret_key: "4uVZ7CVCjzuOg5spOLyeG2Lpf9b97aYF"
  image_proxy: true
search:
  formats:
    - html
    - json
"@ | Set-Content $searxngSettings
            Log-OK "Đã tạo settings.yml cho SearXNG."
        }

        Log-OK "Đang khởi chạy SearXNG Docker container..."
        Push-Location $searxngDir
        try {
            docker compose up -d
            $searxngStarted = $true
            Log-OK "SearXNG đã sẵn sàng tại: http://localhost:8081"
        } catch {
            Log-Warn "Không thể khởi chạy SearXNG: $_"
        } finally {
            Pop-Location
        }
    }

    # 7.2 Cài đặt WebApp qua Docker
    $installWebapp = Read-Host "Bạn có muốn build & chạy Trạm Điều Khiển Web (WebApp) bằng Docker không? (Y/n)"
    if ([string]::IsNullOrWhiteSpace($installWebapp) -or $installWebapp -match "^[Yy]$") {
        Log-OK "Đang build Docker image cho WebApp..."
        try {
            docker compose -f docker-compose.webapp.yml build webapp
            Log-OK "Đang khởi động WebApp container..."
            docker compose -f docker-compose.webapp.yml up -d webapp
            $webappStarted = $true
            Log-OK "WebApp container đã khởi chạy thành công!"
        } catch {
            Log-Warn "Lỗi khi chạy WebApp qua Docker: $_"
        }
    }
} else {
    Log-Warn "Chưa phát hiện Docker Desktop. Bạn có thể cài đặt Docker Desktop từ https://www.docker.com nếu muốn dùng SearXNG."
}

# ---- 8. Hoàn tất ----
Write-Host ""
Log-OK "Cài đặt hoàn tất! 🎉"
Write-Host ""
Write-Host "Các bước tiếp theo:" -ForegroundColor Cyan
Write-Host "  1) Kiểm tra file .env (điền ALLOWED_USERS, ADMIN_USER_IDS nếu cần)."
Write-Host "  2) Đảm bảo Ollama đang chạy: ollama serve"
Write-Host "  3) Chạy bot Telegram:"
Write-Host "       .\venv\Scripts\Activate.ps1"
Write-Host "       python my_bot.py"
Write-Host ""
if ($searxngStarted) {
    Write-Host "  4) SearXNG Web Search: Đang chạy tại http://localhost:8081" -ForegroundColor Green
}
Write-Host "  5) Quản trị Trạm Điều Khiển Web (Dashboard):"
if ($webappStarted) {
    Write-Host "     ● WebApp ĐANG CHẠY qua Docker tại: http://localhost:8080" -ForegroundColor Green
    Write-Host "     - Xem logs container : docker compose -f docker-compose.webapp.yml logs -f webapp"
    Write-Host "     - Dừng WebApp        : docker compose -f docker-compose.webapp.yml down"
} else {
    Write-Host "     - Cách 1 (Docker): docker compose -f docker-compose.webapp.yml up -d"
    Write-Host "     - Cách 2 (Python): .\venv\Scripts\Activate.ps1 ; python -m webapp.main"
}
Write-Host ""
Write-Host "Muốn chạy bot và webapp dạng Windows Service tự khởi động cùng máy tính:" -ForegroundColor Yellow
Write-Host "  Chạy script: .\scripts\install_nssm_service.ps1"