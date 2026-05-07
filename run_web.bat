@echo off
setlocal
cd /d "%~dp0"
set "AUTOTRANSLATE_WORKER_BACKEND=thread"
if exist "%~dp0tools\ffmpeg\bin\ffmpeg.exe" set "PATH=%~dp0tools\ffmpeg\bin;%PATH%"
set "PYTHON_EXE=%~dp0tools\Python312\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=%~dp0tools\Python312\Scripts\python.exe"
if not exist "%PYTHON_EXE%" (
  echo Khong tim thay Python local. Hay chay install_all.bat truoc.
  pause
  exit /b 1
)
"%PYTHON_EXE%" -m app.main web --host 127.0.0.1 --port 8002
