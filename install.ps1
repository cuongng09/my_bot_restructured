# =====================================================================
#  install.ps1 -- Cai dat nhanh Ollama Telegram Bot v6.2 tren Windows
#  Cach dung (PowerShell Administrator khuyen nghi):
#     Set-ExecutionPolicy Unrestricted -Scope Process
#     .\install.ps1
# =====================================================================
#Requires -Version 5.1
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ErrorActionPreference = "Stop"

function Log-OK   { param([string]$msg) Write-Host "[OK] $msg" -ForegroundColor Green }
function Log-Warn { param([string]$msg) Write-Host "[!!] $msg" -ForegroundColor Yellow }
function Log-Err  { param([string]$msg) Write-Host "[LOI] $msg" -ForegroundColor Red }
function Log-Info { param([string]$msg) Write-Host "[--] $msg" -ForegroundColor Cyan }

Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "  Cai dat Ollama Telegram Bot va Web Dashboard (Windows)" -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

$PROJECT_DIR = $PSScriptRoot
Set-Location $PROJECT_DIR
Log-OK "Thu muc du an: $PROJECT_DIR"

# =====================================================================
# 1. KIEM TRA PYTHON
# =====================================================================
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Log-Err "Khong tim thay Python tren he thong!"
    Write-Host "Vui long cai dat Python 3.11 hoac 3.12 tu https://www.python.org (nho tich chon 'Add Python to PATH')."
    exit 1
}
Log-OK "Da phat hien Python: $($pythonCmd.Source)"

# Kiem tra phien ban Python >= 3.9
$pyVersion = & python --version 2>&1
Log-Info "Phien ban Python: $pyVersion"

# =====================================================================
# 2. TAO VA KICH HOAT VIRTUALENV
# =====================================================================
if (-not (Test-Path "venv")) {
    Log-OK "Tao moi truong ao Python (venv)..."
    & python -m venv venv
} else {
    Log-Warn "Da co san thu muc venv\, bo qua buoc tao moi."
}

$venvPython = Join-Path $PROJECT_DIR "venv\Scripts\python.exe"
$venvPip    = Join-Path $PROJECT_DIR "venv\Scripts\pip.exe"

if (-not (Test-Path $venvPython)) {
    Log-Err "Khong tim thay $venvPython -- venv co the bi loi. Xoa thu muc venv\ va chay lai script."
    exit 1
}
Log-OK "Da kich hoat venv tai: $venvPython"

# =====================================================================
# 3. CAI THU VIEN PYTHON
# =====================================================================
if (Test-Path "requirements.txt") {
    Log-OK "Dang nang cap pip va cai dat dependencies tu requirements.txt..."
    & $venvPython -m pip install --upgrade pip
    & $venvPip install -r requirements.txt
    Log-OK "Cai dat thu vien Python thanh cong."
} else {
    Log-Err "Khong tim thay requirements.txt trong $PROJECT_DIR."
    exit 1
}

# =====================================================================
# 4. TAO FILE CAU HINH .env
# =====================================================================
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Log-OK "Da tao file .env tu .env.example."
    } else {
        New-Item -ItemType File -Path ".env" | Out-Null
        Log-Warn "Khong tim thay .env.example, tao file .env trong."
    }

    $tgToken = Read-Host "Nhap TELEGRAM_TOKEN cua ban (lay tu @BotFather)"
    if ($tgToken) {
        $envContent = Get-Content ".env" -Raw -Encoding UTF8
        if ($envContent -match "(?m)^TELEGRAM_TOKEN=") {
            $envContent = $envContent -replace "(?m)^TELEGRAM_TOKEN=.*", "TELEGRAM_TOKEN=$tgToken"
            Set-Content ".env" $envContent -Encoding UTF8
        } else {
            Add-Content ".env" "TELEGRAM_TOKEN=$tgToken" -Encoding UTF8
        }
        Log-OK "Da luu TELEGRAM_TOKEN vao .env."
    } else {
        Log-Warn "Ban chua nhap token -- nho mo .env va dien TELEGRAM_TOKEN truoc khi chay bot."
    }
} else {
    Log-Warn "Da co san file .env, giu nguyen khong ghi de."
}

# Tao cac thu muc du lieu
$null = New-Item -ItemType Directory -Force -Path "voices", "data", "logs"

# =====================================================================
# 5. KIEM TRA OLLAMA
# =====================================================================
$ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue
if ($ollamaCmd) {
    Log-OK "Da phat hien Ollama tren may."
} else {
    Log-Warn "Chua thay lenh 'ollama'. Hay tai va cai dat Ollama tu https://ollama.com roi chay: ollama serve"
}

# =====================================================================
# 6. GOM Y VE VOICE PIPER VA TESSERACT OCR
# =====================================================================
Log-Warn "Neu muon dung TTS (doc giong noi), tai model Piper tieng Viet (.onnx + .onnx.json) tu:"
Log-Warn "  https://huggingface.co/rhasspy/piper-voices (thu muc vi/vi_VN/) va dat vao .\voices\"
Log-Warn "Neu muon dung OCR trich xuat chu trong anh, hay cai Tesseract OCR va khai bao trong .env:"
Log-Warn "  TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe"

# =====================================================================
# 7. DOCKER, SEARXNG VA WEBAPP
# =====================================================================
$dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
$searxngStarted  = $false
$voiceboxStarted = $false
$voiceboxDir     = ""
$webappStarted   = $false

if ($dockerCmd) {
    # Kiem tra Docker daemon co dang chay khong
    $dockerRunning = $false
    try {
        $null = & docker info 2>&1
        $dockerRunning = $true
    } catch {
        Log-Warn "Docker duoc cai nhung daemon chua chay. Hay khoi dong Docker Desktop truoc."
    }

    if ($dockerRunning) {
        Log-OK "Da phat hien Docker Desktop dang hoat dong."

        # ---- 7.1 Cai dat SearXNG ----
        $installSearxng = Read-Host "Ban co muon cai dat va khoi chay SearXNG (Web Search RAG) bang Docker khong? (Y/n)"
        if ([string]::IsNullOrWhiteSpace($installSearxng) -or $installSearxng -match "^[Yy]$") {

            $parentSearxng = Join-Path (Split-Path $PROJECT_DIR -Parent) "searxng"
            $localSearxng  = Join-Path $PROJECT_DIR "searxng"
            $searxngDir    = if (Test-Path $parentSearxng) { $parentSearxng } else { $localSearxng }

            $null = New-Item -ItemType Directory -Force -Path (Join-Path $searxngDir "core-config")

            $searxngEnv = Join-Path $searxngDir ".env"
            if (-not (Test-Path $searxngEnv)) {
                @"
SEARXNG_VERSION=latest
SEARXNG_PORT=8081
"@ | Set-Content $searxngEnv -Encoding UTF8
                Log-OK "Da tao file .env cho SearXNG (Port 8081)."
            }

            $searxngCompose = Join-Path $searxngDir "docker-compose.yml"
            if (-not (Test-Path $searxngCompose)) {
                # Dung dollar literal de tranh PS expand bien
                $dollar = '$'
                @"
services:
  core:
    container_name: searxng-core
    image: searxng/searxng:${dollar}{SEARXNG_VERSION:-latest}
    ports:
      - "${dollar}{SEARXNG_PORT:-8081}:8080"
    volumes:
      - ./core-config:/etc/searxng
    environment:
      - SEARXNG_BASE_URL=http://localhost:${dollar}{SEARXNG_PORT:-8081}/
    restart: unless-stopped
"@ | Set-Content $searxngCompose -Encoding UTF8
                Log-OK "Da tao docker-compose.yml cho SearXNG."
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
"@ | Set-Content $searxngSettings -Encoding UTF8
                Log-OK "Da tao settings.yml cho SearXNG."
            } else {
                $settingsContent = Get-Content $searxngSettings -Raw
                if ($settingsContent -notmatch "json") {
                    Add-Content $searxngSettings "`nsearch:`n  formats:`n    - html`n    - json" -Encoding UTF8
                    Log-OK "Da bat dinh dang json trong settings.yml cua SearXNG."
                }
            }

            Log-OK "Dang khoi chay SearXNG Docker container..."
            Push-Location $searxngDir
            try {
                & docker compose up -d
                $searxngStarted = $true
                Log-OK "SearXNG da san sang tai: http://localhost:8081"
            } catch {
                Log-Warn "Khong the khoi chay SearXNG: $_"
            } finally {
                Pop-Location
            }
        }

        # ---- 7.2 Cai dat WebApp qua Docker ----
        $installWebapp = Read-Host "Ban co muon build va chay Tram Dieu Khien Web (WebApp) bang Docker khong? (Y/n)"
        if ([string]::IsNullOrWhiteSpace($installWebapp) -or $installWebapp -match "^[Yy]$") {
            Log-OK "Dang build Docker image cho WebApp..."
            try {
                & docker compose -f docker-compose.webapp.yml build webapp
                Log-OK "Dang khoi dong WebApp container..."
                & docker compose -f docker-compose.webapp.yml up -d webapp
                $webappStarted = $true
                Log-OK "WebApp container da khoi chay thanh cong!"
            } catch {
                Log-Warn "Loi khi chay WebApp qua Docker: $_"
            }
        }
    }
} else {
    Log-Warn "Chua phat hien Docker Desktop. Cai dat tu https://www.docker.com neu muon dung SearXNG."
}

# =====================================================================
# 8. VOICEBOX STT QUA JUST (https://github.com/jamiepine/voicebox.git)
# =====================================================================
Write-Host ""
$installVoicebox = Read-Host "Ban co muon cai dat Voicebox STT bang 'just' khong? (Y/n)"
if ([string]::IsNullOrWhiteSpace($installVoicebox) -or $installVoicebox -match "^[Yy]$") {
    $parentVoicebox = Join-Path (Split-Path $PROJECT_DIR -Parent) "voicebox"
    $localVoicebox  = Join-Path $PROJECT_DIR "voicebox"
    $voiceboxDir    = if (Test-Path $parentVoicebox) { $parentVoicebox } else { $localVoicebox }

    # ---- Clone repo neu chua co ----
    if (-not (Test-Path (Join-Path $voiceboxDir ".git"))) {
        Log-OK "Dang clone Voicebox tu https://github.com/jamiepine/voicebox.git..."
        & git clone --depth 1 https://github.com/jamiepine/voicebox.git $voiceboxDir
    } else {
        Log-OK "Da co san thu muc Voicebox tai: $voiceboxDir"
    }

    # ---- Kiem tra / cai just ----
    $justCmd = Get-Command just -ErrorAction SilentlyContinue
    if (-not $justCmd) {
        Log-Warn "'just' chua duoc cai. Dang cai qua winget..."
        try {
            & winget install --id Casey.Just -e --source winget --accept-package-agreements --accept-source-agreements
            # Cap nhat lai PATH trong session hien tai
            $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" +
                        [System.Environment]::GetEnvironmentVariable("PATH", "User")
            $justCmd = Get-Command just -ErrorAction SilentlyContinue
        } catch {
            Log-Warn "Khong the cai 'just' qua winget: $_"
            Log-Warn "Cai thu cong: https://github.com/casey/just#installation"
            Log-Warn "Sau khi cai, vao thu muc '$voiceboxDir' va chay: just setup"
            $installVoicebox = "skip"
        }
    }

    if ($installVoicebox -ne "skip" -and $justCmd) {
        # ---- Kiem tra Python tuong thich (Voicebox yeu cau 3.10-3.12) ----
        $vbPython = $null
        foreach ($pyTry in @("python3.12", "python3.11", "python3.10", "python3.13")) {
            if (Get-Command $pyTry -ErrorAction SilentlyContinue) {
                $vbPython = $pyTry; break
            }
        }
        # Neu chi co python3 / python chung -> kiem tra phien ban
        if (-not $vbPython) {
            $defPy = Get-Command python -ErrorAction SilentlyContinue
            if ($defPy) {
                $minor = [int](& python -c "import sys; print(sys.version_info.minor)" 2>$null)
                $major = [int](& python -c "import sys; print(sys.version_info.major)" 2>$null)
                if ($major -eq 3 -and $minor -le 12) { $vbPython = "python" }
            }
        }

        if (-not $vbPython) {
            Log-Warn "Voicebox yeu cau Python 3.10-3.12 (kokoro khong ho tro Python 3.13+)."
            Log-Warn "Dang thu cai Python 3.12 qua winget..."
            try {
                & winget install --id Python.Python.3.12 -e --source winget `
                    --accept-package-agreements --accept-source-agreements
                # Cap nhat PATH
                $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" +
                            [System.Environment]::GetEnvironmentVariable("PATH","User")
                if (Get-Command python3.12 -ErrorAction SilentlyContinue) {
                    $vbPython = "python3.12"
                    Log-OK "Da cai Python 3.12 thanh cong."
                }
            } catch {
                Log-Warn "Khong the cai Python 3.12 tu dong: $_"
            }
            if (-not $vbPython) {
                Log-Warn "Cai thu cong Python 3.12 tai https://www.python.org/downloads/release/python-3129/"
                Log-Warn "Sau khi cai, vao thu muc '$voiceboxDir' va chay: just setup"
                $installVoicebox = "skip"
            }
        } else {
            Log-OK "Se dung $vbPython de tao venv cho Voicebox."
        }
    }

    if ($installVoicebox -ne "skip" -and $justCmd) {
        # ---- Kiem tra bun ----
        $bunCmd = Get-Command bun -ErrorAction SilentlyContinue
        if (-not $bunCmd) {
            Log-Warn "'bun' chua duoc cai. Dang cai qua winget..."
            try {
                & winget install --id Oven-sh.Bun -e --source winget --accept-package-agreements --accept-source-agreements
                $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" +
                            [System.Environment]::GetEnvironmentVariable("PATH", "User")
            } catch {
                Log-Warn "Khong the cai 'bun' tu dong. Cai thu cong: https://bun.sh"
            }
        }

        Log-OK "Dang chay 'just setup' trong $voiceboxDir (co the mat vai phut, tu detect GPU)..."
        Push-Location $voiceboxDir
        try {
            & just setup
            $voiceboxStarted = $true
            Log-OK "Voicebox STT da duoc cai dat xong."
        } catch {
            Log-Warn "Loi khi chay 'just setup': $_"
        } finally {
            Pop-Location
        }
    }
}

# =====================================================================
# 9. CAI WINDOWS SERVICE NSSM (tuy chon)
# =====================================================================
Write-Host ""
$nssmScript = Join-Path $PROJECT_DIR "scripts\install_nssm_service.ps1"
$installNssm = Read-Host "Ban co muon cai bot chay tu dong khi khoi dong Windows (dung NSSM Service)? (Y/n)"
$nssmInstalled = $false
if ([string]::IsNullOrWhiteSpace($installNssm) -or $installNssm -match "^[Yy]$") {
    if (Test-Path $nssmScript) {
        try {
            & $nssmScript
            $nssmInstalled = $true
        } catch {
            Log-Warn "Loi khi cai NSSM service: $_"
            Log-Warn "Ban co the chay thu cong sau: .\scripts\install_nssm_service.ps1"
        }
    } else {
        Log-Warn "Khong tim thay script '$nssmScript'. Cai thu cong sau."
    }
}

# =====================================================================
# 10. HOAN TAT
# =====================================================================
Write-Host ""
Log-OK "Cai dat hoan tat!"
Write-Host ""
Write-Host "Cac buoc tiep theo:" -ForegroundColor Cyan
Write-Host "  1) Kiem tra file .env (dien ALLOWED_USERS, ADMIN_USER_IDS neu can)."
Write-Host "  2) Dam bao Ollama dang chay: ollama serve"
if ($nssmInstalled) {
    Write-Host "  3) Bot Telegram: dang chay ngam qua Windows Service (MyBotTelegram)" -ForegroundColor Green
    Write-Host "     - Xem logs  : Get-Content logs\bot.log -Wait -Tail 30"
    Write-Host "     - Dung       : nssm stop MyBotTelegram"
    Write-Host "     - Khoi lai   : nssm restart MyBotTelegram"
    Write-Host "     - Go service : .\scripts\uninstall_nssm_service.ps1"
} else {
    Write-Host "  3) Chay bot Telegram:"
    Write-Host "       .\venv\Scripts\Activate.ps1"
    Write-Host "       $env:PYTHONPATH="src"; python -m main"
}
Write-Host ""
if ($searxngStarted) {
    Write-Host "  4) SearXNG Web Search: Dang chay tai http://localhost:8081" -ForegroundColor Green
}
if ($voiceboxStarted) {
    Write-Host "  5) Voicebox STT: Da cai dat xong tai $voiceboxDir" -ForegroundColor Green
    Write-Host "     - Khoi chay backend : cd `"$voiceboxDir`" ; just dev-backend"
    Write-Host "       -> API chay tai    : http://localhost:17493"
    Write-Host "     - Dung backend      : Ctrl+C trong terminal dang chay"
    Write-Host "     - Cap nhat / cai lai: cd `"$voiceboxDir`" ; just setup"
}
Write-Host "  6) Quan tri Tram Dieu Khien Web (Dashboard):"
if ($webappStarted) {
    Write-Host "     * WebApp DANG CHAY qua Docker tai: http://localhost:8080" -ForegroundColor Green
    Write-Host "     - Xem logs  : docker compose -f docker-compose.webapp.yml logs -f webapp"
    Write-Host "     - Dung       : docker compose -f docker-compose.webapp.yml down"
    Write-Host "     - Khoi lai   : docker compose -f docker-compose.webapp.yml restart webapp"
} else {
    Write-Host "     - Cach 1 (Docker): docker compose -f docker-compose.webapp.yml up -d"
    Write-Host "     - Cach 2 (Python): .\venv\Scripts\Activate.ps1 ; python -m webapp.main"
}
Write-Host ""
Write-Host "Muon chay bot dang Windows Service tu khoi dong cung may tinh:" -ForegroundColor Yellow
Write-Host "  Chay script: .\scripts\install_nssm_service.ps1"
Write-Host ""