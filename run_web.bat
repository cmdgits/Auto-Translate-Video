@echo off
setlocal
cd /d "%~dp0"
set "AUTOTRANSLATE_WORKER_BACKEND=thread"
if exist "%~dp0tools\ffmpeg\bin\ffmpeg.exe" set "PATH=%~dp0tools\ffmpeg\bin;%PATH%"
"%~dp0tools\Python312\python.exe" -m app.main web --host 127.0.0.1 --port 8001
