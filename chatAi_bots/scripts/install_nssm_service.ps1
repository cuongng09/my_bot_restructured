<#
.SYNOPSIS
    Cài my_bot.py (và tùy chọn Trạm Điều Khiển Web) chạy tự động dưới dạng Windows Service,
    dùng NSSM (https://nssm.cc) — tự khởi động cùng Windows, tự restart nếu crash.

.DESCRIPTION
    - Service "MyBotTelegram" : chạy `python my_bot.py`
    - Service "MyBotWebapp"   : chạy `python -m webapp.main` (chỉ cài nếu -WithWebapp)
    Cả hai đều dùng đúng venv của dự án, AppDirectory = thư mục gốc (nơi có config.py),
    log stdout/stderr riêng vào logs\ (ngoài log nội bộ bot_logger.py đã có).

.PARAMETER NssmPath
    Đường dẫn tới nssm.exe. Mặc định tìm trong PATH hoặc .\scripts\nssm.exe.

.PARAMETER WithWebapp
    Thêm switch này để cài luôn service cho Trạm Điều Khiển Web.

.EXAMPLE
    # Chạy trong PowerShell với quyền Administrator, từ thư mục gốc dự án:
    .\scripts\install_nssm_service.ps1

.EXAMPLE
    .\scripts\install_nssm_service.ps1 -WithWebapp

.NOTES
    BẮT BUỘC chạy PowerShell với quyền Administrator ("Run as administrator"),
    nếu không nssm.exe sẽ báo lỗi không tạo được service.
#>

[CmdletBinding()]
param(
    [string]$NssmPath = "",
    [switch]$WithWebapp
)

$ErrorActionPreference = "Stop"

# ── 0. Kiểm tra quyền Administrator ─────────────────────────────────────────
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "❌ Script này cần chạy với quyền Administrator." -ForegroundColor Red
    Write-Host "   Mở PowerShell bằng 'Run as administrator' rồi chạy lại." -ForegroundColor Yellow
    exit 1
}

# ── 1. Tìm nssm.exe ──────────────────────────────────────────────────────────
if ([string]::IsNullOrWhiteSpace($NssmPath)) {
    $candidate = Get-Command nssm.exe -ErrorAction SilentlyContinue
    if ($candidate) {
        $NssmPath = $candidate.Source
    } elseif (Test-Path "$PSScriptRoot\nssm.exe") {
        $NssmPath = "$PSScriptRoot\nssm.exe"
    } else {
        Write-Host "❌ Không tìm thấy nssm.exe." -ForegroundColor Red
        Write-Host "   Tải tại https://nssm.cc/download, giải nén, copy nssm.exe" -ForegroundColor Yellow
        Write-Host "   (bản win64) vào thư mục '.\scripts\' rồi chạy lại script này." -ForegroundColor Yellow
        exit 1
    }
}
Write-Host "✅ Dùng nssm tại: $NssmPath" -ForegroundColor Green

# ── 2. Xác định đường dẫn dự án ──────────────────────────────────────────────
$ProjectRoot = (Resolve-Path "$PSScriptRoot\..").Path
$VenvPython  = Join-Path $ProjectRoot "venv\Scripts\python.exe"
$LogsDir     = Join-Path $ProjectRoot "logs"

if (-not (Test-Path $VenvPython)) {
    Write-Host "❌ Không tìm thấy venv tại: $VenvPython" -ForegroundColor Red
    Write-Host "   Kiểm tra bạn đã tạo venv đúng tên 'venv' trong thư mục gốc dự án chưa," -ForegroundColor Yellow
    Write-Host "   hoặc sửa lại biến `$VenvPython trong script này nếu venv ở nơi khác." -ForegroundColor Yellow
    exit 1
}
if (-not (Test-Path (Join-Path $ProjectRoot "config.py"))) {
    Write-Host "❌ Không thấy config.py tại '$ProjectRoot' — script phải nằm trong thư mục scripts\ của dự án." -ForegroundColor Red
    exit 1
}
New-Item -ItemType Directory -Force -Path $LogsDir | Out-Null

Write-Host "📁 Thư mục dự án : $ProjectRoot"
Write-Host "🐍 Python (venv)  : $VenvPython"
Write-Host ""

# ── 3. Hàm cài 1 service ──────────────────────────────────────────────────────
function Install-BotService {
    param(
        [string]$ServiceName,
        [string]$Arguments,
        [string]$DisplayName,
        [string]$Description
    )

    $existing = & $NssmPath status $ServiceName 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "⚠️  Service '$ServiceName' đã tồn tại — dừng & gỡ trước khi cài lại..." -ForegroundColor Yellow
        & $NssmPath stop $ServiceName 2>$null | Out-Null
        & $NssmPath remove $ServiceName confirm 2>$null | Out-Null
        Start-Sleep -Seconds 1
    }

    Write-Host "🔧 Đang cài service '$ServiceName'..."
    & $NssmPath install $ServiceName $VenvPython $Arguments
    & $NssmPath set $ServiceName AppDirectory $ProjectRoot
    & $NssmPath set $ServiceName DisplayName $DisplayName
    & $NssmPath set $ServiceName Description $Description
    & $NssmPath set $ServiceName Start SERVICE_AUTO_START

    # Tự restart nếu crash, chờ 5s giữa các lần restart (tránh vòng lặp restart dồn dập)
    & $NssmPath set $ServiceName AppExit Default Restart
    & $NssmPath set $ServiceName AppRestartDelay 5000

    # Log stdout/stderr riêng của service (bổ sung cho log nội bộ logs\bot.log đã có),
    # tự xoay vòng file khi > 10MB hoặc mỗi 24h.
    $stdout = Join-Path $LogsDir "$ServiceName.out.log"
    $stderr = Join-Path $LogsDir "$ServiceName.err.log"
    & $NssmPath set $ServiceName AppStdout $stdout
    & $NssmPath set $ServiceName AppStderr $stderr
    & $NssmPath set $ServiceName AppRotateFiles 1
    & $NssmPath set $ServiceName AppRotateOnline 1
    & $NssmPath set $ServiceName AppRotateSeconds 86400
    & $NssmPath set $ServiceName AppRotateBytes 10485760

    Write-Host "▶️  Khởi động '$ServiceName'..."
    & $NssmPath start $ServiceName

    Start-Sleep -Seconds 2
    $status = & $NssmPath status $ServiceName
    Write-Host "   Trạng thái: $status" -ForegroundColor Cyan
    Write-Host ""
}

# ── 4. Cài service bot Telegram (luôn cài) ───────────────────────────────────
Install-BotService `
    -ServiceName "MyBotTelegram" `
    -Arguments "my_bot.py" `
    -DisplayName "My Bot - Telegram AI Assistant" `
    -Description "Bot Telegram AI chay qua Ollama local. Quan ly boi NSSM."

# ── 5. Cài service Trạm Điều Khiển Web (tùy chọn) ─────────────────────────────
if ($WithWebapp) {
    Install-BotService `
        -ServiceName "MyBotWebapp" `
        -Arguments "-m webapp.main" `
        -DisplayName "My Bot - Tram Dieu Khien Web" `
        -Description "Dashboard quan tri web cho My Bot (webapp/main.py). Quan ly boi NSSM."
}

# ── 6. Tổng kết ────────────────────────────────────────────────────────────────
Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "✅ HOÀN TẤT" -ForegroundColor Green
Write-Host "════════════════════════════════════════════════════════"
Write-Host ""
Write-Host "Kiểm tra service đang chạy:"
Write-Host "  Get-Service MyBotTelegram" + $(if ($WithWebapp) { ", MyBotWebapp" } else { "" })
Write-Host "  hoặc mở services.msc → tìm 'My Bot - ...'"
Write-Host ""
Write-Host "Xem log trực tiếp:"
Write-Host "  Get-Content '$LogsDir\bot.log' -Wait -Tail 30"
Write-Host ""
Write-Host "⚠️  QUAN TRỌNG: từ giờ KHÔNG chạy tay 'python my_bot.py' trong terminal nữa —" -ForegroundColor Yellow
Write-Host "   nếu chạy chung với service, Telegram sẽ báo lỗi Conflict (2 tiến trình" -ForegroundColor Yellow
Write-Host "   cùng poll 1 token). Dùng 'nssm stop MyBotTelegram' rồi mới được chạy tay." -ForegroundColor Yellow
Write-Host ""
Write-Host "Các lệnh NSSM hữu ích:"
Write-Host "  nssm stop MyBotTelegram      # dừng service"
Write-Host "  nssm restart MyBotTelegram   # khởi động lại"
Write-Host "  nssm edit MyBotTelegram      # mở GUI chỉnh cấu hình"
Write-Host "  .\scripts\uninstall_nssm_service.ps1   # gỡ toàn bộ service"
