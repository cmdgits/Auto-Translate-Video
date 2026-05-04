@echo off
setlocal
cd /d "%~dp0"
"%~dp0tools\Python312\python.exe" -m app.main web --host 127.0.0.1 --port 8001
