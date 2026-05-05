$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $projectRoot "tools\Python312\python.exe"
if (-not (Test-Path $python)) {
  $python = Join-Path $projectRoot "tools\Python312\Scripts\python.exe"
}

if (-not (Test-Path $python)) {
  Write-Error "Không tìm thấy Python local. Hãy chạy install_all.bat trước."
}

Set-Location $projectRoot
$env:AUTOTRANSLATE_WORKER_BACKEND = "thread"
$ffmpegBin = Join-Path $projectRoot "tools\ffmpeg\bin"
if (Test-Path (Join-Path $ffmpegBin "ffmpeg.exe")) {
  $env:PATH = "$ffmpegBin;$env:PATH"
}
$tesseractExe = Join-Path $projectRoot "tools\Tesseract-OCR\tesseract.exe"
if (Test-Path $tesseractExe) {
  $tesseractDir = Split-Path -Parent $tesseractExe
  $env:TESSERACT_CMD = $tesseractExe
  $env:TESSDATA_PREFIX = Join-Path $tesseractDir "tessdata"
  $env:PATH = "$tesseractDir;$env:PATH"
}
& $python -m app.main web --host 127.0.0.1 --port 8001
