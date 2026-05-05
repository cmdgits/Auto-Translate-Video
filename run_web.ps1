$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $projectRoot "tools\Python312\python.exe"

if (-not (Test-Path $python)) {
  Write-Error "Không tìm thấy $python. Hãy kiểm tra thư mục tools\Python312."
}

Set-Location $projectRoot
$env:AUTOTRANSLATE_WORKER_BACKEND = "thread"
& $python -m app.main web --host 127.0.0.1 --port 8001
