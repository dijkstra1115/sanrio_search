<#
.SYNOPSIS
    One-click startup script for sanrio_search on Windows.
    Installs missing dependencies, starts ngrok tunnel (background),
    then runs uvicorn in the foreground.

.USAGE
    Double-click start.bat
    or:  powershell -ExecutionPolicy Bypass -File scripts\start.ps1
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Config ───────────────────────────────────────────────────────
$NGROK_DOMAIN = "mortuary-tag-goofiness.ngrok-free.dev"

$ROOT = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Definition)
Set-Location $ROOT
[System.IO.Directory]::SetCurrentDirectory($ROOT)

# ── Colours ──────────────────────────────────────────────────────
function Write-Step  { param($m) Write-Host "[*] $m" -ForegroundColor Cyan }
function Write-Ok    { param($m) Write-Host "[+] $m" -ForegroundColor Green }
function Write-Warn  { param($m) Write-Host "[!] $m" -ForegroundColor Yellow }
function Write-Err   { param($m) Write-Host "[-] $m" -ForegroundColor Red }

# ── 1. Check / load .env ─────────────────────────────────────────
Write-Step "Loading environment variables"

$envFile = Join-Path $ROOT ".env"
if (-not (Test-Path $envFile)) {
    Write-Warn ".env not found - copying from .env.example"
    Copy-Item (Join-Path $ROOT ".env.example") $envFile
    Write-Err "Please edit .env and fill in LINE_CHANNEL_SECRET and LINE_CHANNEL_ACCESS_TOKEN, then re-run."
    Read-Host "Press Enter to exit"
    exit 1
}

Get-Content $envFile | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith("#")) {
        $parts = $line -split "=", 2
        if ($parts.Count -eq 2) {
            Set-Item -Path "Env:\$($parts[0].Trim())" -Value $parts[1].Trim()
        }
    }
}

if (-not $env:LINE_CHANNEL_SECRET -or $env:LINE_CHANNEL_SECRET -eq "your_line_channel_secret") {
    Write-Err "LINE_CHANNEL_SECRET is not set. Please edit .env first."
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Ok ".env loaded"

# ── 2. Check Python ──────────────────────────────────────────────
Write-Step "Checking Python"
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Err "Python not found. Install from https://www.python.org/downloads/ and re-run."
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Ok "Python: $(python --version 2>&1)"

# ── 3. Check Node.js ─────────────────────────────────────────────
Write-Step "Checking Node.js"
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Err "Node.js not found. Install from https://nodejs.org/ and re-run."
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Ok "Node: $(node --version 2>&1)"

# ── 4. Install pip dependencies ──────────────────────────────────
Write-Step "Installing Python dependencies"
pip install -q -r (Join-Path $ROOT "requirements.txt") 2>&1 | Out-Null
Write-Ok "Python dependencies ready"

# ── 5. Check playwright-cli ──────────────────────────────────────
Write-Step "Checking playwright-cli"
if (-not (Get-Command playwright-cli.cmd -ErrorAction SilentlyContinue)) {
    Write-Step "Installing playwright-cli globally"
    npm install -g @playwright/cli@latest 2>&1 | Out-Null
}
Write-Ok "playwright-cli ready"

# ── 6. Check ngrok ───────────────────────────────────────────────
Write-Step "Checking ngrok"
if (-not (Get-Command ngrok -ErrorAction SilentlyContinue)) {
    Write-Step "Installing ngrok via winget (one-time)"
    winget install --id ngrok.ngrok --accept-source-agreements --accept-package-agreements
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
    if (-not (Get-Command ngrok -ErrorAction SilentlyContinue)) {
        Write-Err "ngrok install failed. Install manually: winget install ngrok.ngrok"
        Read-Host "Press Enter to exit"
        exit 1
    }
}
Write-Ok "ngrok ready"

# ── 7. Start ngrok (background) ─────────────────────────────────
Write-Step "Starting ngrok tunnel (domain: $NGROK_DOMAIN)"
$ngrokLogFile = Join-Path $ROOT "logs_ngrok.txt"
if (Test-Path $ngrokLogFile) { Remove-Item $ngrokLogFile }

$ngrokProc = Start-Process ngrok `
    -ArgumentList "http", "--domain=$NGROK_DOMAIN", "8080", "--log=file", "--log-format=term", "--log-level=info", "--log=$ngrokLogFile" `
    -PassThru -WindowStyle Hidden

$ready = $false
$waited = 0
while ($waited -lt 20) {
    Start-Sleep -Seconds 1
    $waited++
    if (Test-Path $ngrokLogFile) {
        $match = Select-String -Path $ngrokLogFile -Pattern "started tunnel" -SimpleMatch | Select-Object -First 1
        if ($match) { $ready = $true; break }
    }
}

if (-not $ready) {
    Write-Err "ngrok failed to start. Check logs_ngrok.txt"
    if (Test-Path $ngrokLogFile) { Get-Content $ngrokLogFile -Tail 5 }
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Ok "ngrok tunnel ready"

# ── 8. Print info & run uvicorn (foreground) ─────────────────────
$webhookUrl = "https://$NGROK_DOMAIN/webhook"

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Service is running!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Webhook URL: " -NoNewline; Write-Host $webhookUrl -ForegroundColor Yellow
Write-Host ""
Write-Host "  LINE Developers Console Webhook URL:" -ForegroundColor Cyan
Write-Host "    $webhookUrl" -ForegroundColor White
Write-Host ""
Write-Host "  This URL is fixed - set it once in LINE Console." -ForegroundColor DarkGray
Write-Host "  Press Ctrl+C to stop." -ForegroundColor DarkGray
Write-Host ""

try {
    & python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
}
finally {
    Write-Warn "Shutting down..."
    if (-not $ngrokProc.HasExited) { Stop-Process -Id $ngrokProc.Id -Force -ErrorAction SilentlyContinue }
    Write-Ok "Stopped."
}
