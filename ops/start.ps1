# Blue Balance: one-command offline start (Windows PowerShell 5.1).
# Starts local Ollama (127.0.0.1 only), preloads both models, seeds the DB if missing, then serves the app.
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot

$env:PYTHONUTF8 = '1'
$env:HF_HUB_OFFLINE = '1'
$env:HF_HUB_DISABLE_TELEMETRY = '1'
$env:DO_NOT_TRACK = '1'
$env:OLLAMA_MODELS = 'E:\ollama\models'
$env:OLLAMA_HOST = '127.0.0.1:11434'
$env:OLLAMA_NO_CLOUD = '1'
$env:OLLAMA_KEEP_ALIVE = '-1'
$env:OLLAMA_CONTEXT_LENGTH = '8192'

function Test-Ollama {
    try { Invoke-WebRequest -UseBasicParsing http://127.0.0.1:11434/api/version -TimeoutSec 3 | Out-Null; return $true } catch { return $false }
}

if (-not (Test-Ollama)) {
    Write-Host 'Starting Ollama on 127.0.0.1:11434 ...'
    Start-Process -FilePath 'E:\ollama\bin\ollama.exe' -ArgumentList 'serve' -WindowStyle Hidden
    for ($i = 0; $i -lt 30 -and -not (Test-Ollama); $i++) { Start-Sleep -Seconds 1 }
}

foreach ($model in @('qwen3.5:4b', 'gemma4:e4b-it-qat')) {
    Write-Host "Preloading $model ..."
    $body = @{ model = $model; prompt = ''; keep_alive = -1 } | ConvertTo-Json
    Invoke-RestMethod -Method Post -Uri http://127.0.0.1:11434/api/generate -Body $body -ContentType 'application/json' -TimeoutSec 300 | Out-Null
}

Set-Location (Join-Path $repo 'backend')
if (-not (Test-Path 'E:\blue-balance-data\bb.sqlite')) {
    Write-Host 'Seeding the demo database ...'
    python -m bb.seed
}

Start-Process 'chrome.exe' 'http://127.0.0.1:8000/'
python -m uvicorn bb.api:app --host 127.0.0.1 --port 8000
