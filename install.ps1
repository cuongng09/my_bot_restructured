# =====================================================================
#  install.ps1 — Cài đặt nhanh Ollama Telegram Bot v6.2 (Windows)
#  Dựa theo hướng dẫn "Trên Windows" trong README.md của dự án.
#
#  Cách dùng (PowerShell, không cần Admin để chạy bước cuối,
#  nhưng winget cài phần mềm có thể cần Admin tùy máy):
#     Set-ExecutionPolicy Unrestricted -Scope Process
#     .\install.ps1
# =====================================================================

$ErrorActionPreference = "Stop"

function Log($msg)  { Write-Host "[OK] $msg" -ForegroundColor Green }
function Warn($msg) { Write-Host "[!!] $msg" -ForegroundColor Yellow }
function Err($msg)  { Write-Host "[LỖI] $msg" -ForegroundColor Red }

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectDir
Log "Thư mục dự án: $ProjectDir"

# ---- 0. Kiểm tra winget ----
if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    Err "Không tìm thấy winget. Cài 'App Installer' từ Microsoft Store rồi chạy lại script."
    exit 1
}

# ---- 1. Cài Python, FFmpeg, Tesseract OCR qua winget ----
Log "Đang cài Python 3.11 (bỏ qua nếu đã có)..."
winget install --id Python.Python.3.11 -e --accept-source-agreements --accept-package-agreements

Log "Đang cài FFmpeg (bỏ qua nếu đã có)..."
winget install --id Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements

Log "Đang cài Tesseract OCR (bỏ qua nếu đã có)..."
winget install --id UB-Mannheim.TesseractOCR -e --accept-source-agreements --accept-package-agreements

Warn "Nếu vừa cài xong, có thể cần MỞ LẠI PowerShell để lệnh 'python' được nhận diện (PATH mới)."

# ---- 2. Tạo & kích hoạt virtualenv ----
if (-not (Test-Path "venv")) {
    Log "Tạo môi trường ảo Python (venv)..."
    python -m venv venv
} else {
    Warn "Đã có sẵn thư mục venv\, bỏ qua bước tạo mới."
}

Set-ExecutionPolicy Unrestricted -Scope Process -Force
. .\venv\Scripts\Activate.ps1
Log "Đã kích hoạt venv."

# ---- 3. Cài thư viện Python ----
if (Test-Path "requirements.txt") {
    Log "Đang cài thư viện từ requirements.txt (có thể mất vài phút)..."
    python.exe -m pip install --upgrade pip
    pip install -r requirements.txt
} else {
    Err "Không tìm thấy requirements.txt trong $ProjectDir. Kiểm tra lại bạn đã copy đủ mã nguồn chưa."
    exit 1
}

# ---- 4. Tạo file cấu hình .env ----
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Log "Đã tạo file .env từ .env.example."
    } else {
        Warn "Không tìm thấy .env.example, tạo file .env trống."
        New-Item -Path ".env" -ItemType File | Out-Null
    }

    $TgToken = Read-Host "Nhập TELEGRAM_TOKEN của bạn (lấy từ @BotFather)"
    if ($TgToken) {
        $envContent = Get-Content ".env" -Raw -ErrorAction SilentlyContinue
        if ($envContent -match "(?m)^TELEGRAM_TOKEN=.*$") {
            $envContent = $envContent -replace "(?m)^TELEGRAM_TOKEN=.*$", "TELEGRAM_TOKEN=$TgToken"
            Set-Content ".env" $envContent
        } else {
            Add-Content ".env" "TELEGRAM_TOKEN=$TgToken"
        }
        Log "Đã lưu TELEGRAM_TOKEN vào .env."
    } else {
        Warn "Bạn chưa nhập token — nhớ mở .env và điền TELEGRAM_TOKEN trước khi chạy bot."
    }
} else {
    Warn "Đã có sẵn file .env, giữ nguyên không ghi đè."
}

New-Item -ItemType Directory -Force -Path "voices", "data", "logs" | Out-Null

# ---- 5. Kiểm tra Ollama ----
if (Get-Command ollama -ErrorAction SilentlyContinue) {
    Log "Đã phát hiện Ollama trên máy."
} else {
    Warn "Chưa thấy lệnh 'ollama'. Cài Ollama trước tại https://ollama.com rồi chạy: ollama serve"
}

# ---- 6. Nhắc về model giọng nói Piper (tùy chọn) ----
Warn "Nếu muốn dùng TTS (đọc giọng nói), tải model Piper tiếng Việt (.onnx + .onnx.json) từ"
Warn "  https://huggingface.co/rhasspy/piper-voices (thư mục vi/vi_VN/) và đặt vào .\voices\"
Warn "rồi khai báo qua biến PIPER_VOICE_PATHS trong .env."

# ---- 7. Hoàn tất ----
Write-Host ""
Log "Cài đặt hoàn tất! 🎉"
Write-Host ""
Write-Host "Các bước tiếp theo:"
Write-Host "  1) Kiểm tra lại file .env (điền ALLOWED_USERS, ADMIN_USER_IDS nếu cần)."
Write-Host "  2) Đảm bảo Ollama đang chạy: ollama serve"
Write-Host "  3) Chạy thử bot:"
Write-Host "       .\venv\Scripts\Activate.ps1"
Write-Host "       python my_bot.py"
Write-Host ""
Write-Host "  (Tùy chọn) Chạy dashboard web:"
Write-Host "       python -m webapp.main"
Write-Host ""
Write-Host "Muốn chạy bot tự khởi động cùng Windows (NSSM service), xem phần"
Write-Host "'Chạy dưới dạng Windows Service' trong README.md, ví dụ:"
Write-Host "       .\scripts\install_nssm_service.ps1 -WithWebapp"
