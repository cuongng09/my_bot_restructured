<#
.SYNOPSIS
    Gỡ bỏ các Windows Service đã cài bằng install_nssm_service.ps1.

.EXAMPLE
    .\scripts\uninstall_nssm_service.ps1
#>

[CmdletBinding()]
param(
    [string]$NssmPath = ""
)

$ErrorActionPreference = "Continue"

$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "❌ Script này cần chạy với quyền Administrator." -ForegroundColor Red
    exit 1
}

if ([string]::IsNullOrWhiteSpace($NssmPath)) {
    $candidate = Get-Command nssm.exe -ErrorAction SilentlyContinue
    if ($candidate) {
        $NssmPath = $candidate.Source
    } elseif (Test-Path "$PSScriptRoot\nssm.exe") {
        $NssmPath = "$PSScriptRoot\nssm.exe"
    } else {
        Write-Host "❌ Không tìm thấy nssm.exe." -ForegroundColor Red
        exit 1
    }
}

foreach ($svc in @("MyBotTelegram", "MyBotWebapp")) {
    $status = & $NssmPath status $svc 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "🛑 Đang dừng & gỡ '$svc'..."
        & $NssmPath stop $svc 2>$null | Out-Null
        Start-Sleep -Seconds 1
        & $NssmPath remove $svc confirm
        Write-Host "✅ Đã gỡ '$svc'." -ForegroundColor Green
    } else {
        Write-Host "ℹ️  Service '$svc' không tồn tại, bỏ qua."
    }
}

Write-Host ""
Write-Host "Xong. Có thể chạy tay lại bằng 'python my_bot.py' như bình thường."
