# =====================================================================
#  uninstall.ps1 -- Go bo cai dat Ollama Telegram Bot, WebApp va SearXNG (Windows)
#  Cach dung (PowerShell Administrator khuyen nghi):
#     Set-ExecutionPolicy Unrestricted -Scope Process
#     .\uninstall.ps1
# =====================================================================
#Requires -Version 5.1
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ErrorActionPreference = "Continue"

function Log-OK   { param([string]$msg) Write-Host "[OK] $msg" -ForegroundColor Green }
function Log-Warn { param([string]$msg) Write-Host "[!!] $msg" -ForegroundColor Yellow }
function Log-Err  { param([string]$msg) Write-Host "[LOI] $msg" -ForegroundColor Red }
function Log-Info { param([string]$msg) Write-Host "[--] $msg" -ForegroundColor Cyan }

$PROJECT_DIR = $PSScriptRoot
Set-Location $PROJECT_DIR

Write-Host "=====================================================" -ForegroundColor Red
Write-Host "         CANH BAO: GO CAI DAT (WINDOWS)             " -ForegroundColor Red
Write-Host "=====================================================" -ForegroundColor Red
Write-Host "Thao tac nay se don dep:"
Write-Host "  1. Cac dich vu Windows Service (NSSM neu co)"
Write-Host "  2. WebApp Docker container"
Write-Host "  3. SearXNG Docker container"
Write-Host "  4. Moi truong ao Python (venv)"
Write-Host "  5. Du lieu bot (data, logs, voices - tuy chon)"
Write-Host "  6. File cau hinh .env (tuy chon)"
Write-Host ""

$confirm = Read-Host "Ban co chac chan muon tiep tuc go cai dat? (y/N)"
if ($confirm -notmatch "^[Yy]$") {
    Write-Host "Da huy thao tac."
    exit 0
}

# =====================================================================
# 1. GO WINDOWS SERVICE NSSM NEU CO
# =====================================================================
$uninstallNssm = Join-Path $PROJECT_DIR "scripts\uninstall_nssm_service.ps1"
if (Test-Path $uninstallNssm) {
    Log-OK "Dang kiem tra va go bo Windows Service (NSSM)..."
    try {
        & $uninstallNssm
        Log-OK "Da go bo Windows Service."
    } catch {
        Log-Warn "Loi khi go NSSM service: $_"
    }
} else {
    Log-Info "Khong tim thay script NSSM ($uninstallNssm), bo qua buoc nay."
}

# =====================================================================
# 2+3. GO BO DOCKER CONTAINERS (WEBAPP + SEARXNG)
# =====================================================================
$dockerCmd = Get-Command docker -ErrorAction SilentlyContinue

if ($dockerCmd) {
    # Kiem tra Docker daemon co dang chay khong
    $dockerRunning = $false
    try {
        $null = & docker info *>$null
        $dockerRunning = $LASTEXITCODE -eq 0
    } catch {
        $dockerRunning = $false
    }

    if ($dockerRunning) {
        Log-OK "Da phat hien Docker Desktop dang hoat dong."

        # ---- 2. Gỡ WebApp container ----
        Log-OK "Dang dung va don dep WebApp Docker container..."
        try {
            & docker compose -f docker-compose.webapp.yml down -v *>$null
            & docker rm -f telegram-bot-webapp *>$null
            Log-OK "Da go WebApp container."
        } catch {
            Log-Warn "Khong the dung WebApp container: $_"
        }

        # ---- 3. Gỡ SearXNG container ----
        Log-OK "Dang kiem tra va don dep SearXNG container..."
        $parentSearxng = Join-Path (Split-Path $PROJECT_DIR -Parent) "searxng"
        $localSearxng  = Join-Path $PROJECT_DIR "searxng"
        $searxngDir    = if (Test-Path $parentSearxng) { $parentSearxng } else { $localSearxng }

        if (Test-Path $searxngDir) {
            Push-Location $searxngDir
            try {
                & docker compose down -v *>$null
                Log-OK "Da dung SearXNG container (giu nguyen thu muc cau hinh)."
            } catch {
                Log-Warn "Khong the dung SearXNG container: $_"
            } finally {
                Pop-Location
            }
        } else {
            Log-Info "Khong tim thay thu muc searxng\, bo qua."
        }
    } else {
        Log-Warn "Docker duoc cai nhung daemon chua chay. Bo qua viec dung container."
        Log-Warn "Hay khoi dong Docker Desktop va chay lai script neu can don dep container."
    }
} else {
    Log-Info "Khong phat hien Docker -- bo qua buoc don dep container."
}

# =====================================================================
# 4. XOA MOI TRUONG AO PYTHON (VENV)
# =====================================================================
if (Test-Path "venv") {
    Log-OK "Dang xoa moi truong ao Python (venv)..."
    Remove-Item -Recurse -Force "venv" -ErrorAction SilentlyContinue
    Log-OK "Da xoa thu muc venv\."
} else {
    Log-Info "Khong tim thay thu muc venv\, bo qua."
}

# =====================================================================
# 5. TUY CHON XOA DU LIEU (data, logs, voices)
# =====================================================================
$removeData = Read-Host "Ban co muon xoa du lieu bot (data, logs, voices)? (y/N)"
if ($removeData -match "^[Yy]$") {
    foreach ($folder in @("data", "logs", "voices")) {
        if (Test-Path $folder) {
            Get-ChildItem -Path $folder -Recurse -File -Force |
                Where-Object { $_.Name -ne ".gitkeep" } |
                Remove-Item -Force -ErrorAction SilentlyContinue

            Get-ChildItem -Path $folder -Recurse -Directory -Force |
                Where-Object { (Get-ChildItem $_.FullName -Force).Count -eq 0 } |
                Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
    $null = New-Item -ItemType Directory -Force -Path "data\reports", "logs", "voices"
    foreach ($gk in @("data\.gitkeep", "data\reports\.gitkeep", "logs\.gitkeep", "voices\.gitkeep")) {
        if (-not (Test-Path $gk)) {
            New-Item -ItemType File -Force -Path $gk | Out-Null
        }
    }
    Log-OK "Da don dep du lieu trong data, logs, voices (giu nguyen cac file .gitkeep)."
} else {
    Log-Warn "Giu lai cac thu muc du lieu data, logs, voices."
}

# =====================================================================
# 6. TUY CHON XOA FILE .env
# =====================================================================
$removeEnv = Read-Host "Ban co muon xoa file cau hinh .env? (y/N)"
if ($removeEnv -match "^[Yy]$") {
    if (Test-Path ".env") {
        Remove-Item -Force ".env" -ErrorAction SilentlyContinue
        Log-OK "Da xoa file .env."
    } else {
        Log-Info "Khong tim thay file .env, bo qua."
    }
} else {
    Log-Warn "Giu lai file .env."
}

Write-Host ""
Log-OK "Go cai dat tren Windows hoan tat!"
Write-Host ""