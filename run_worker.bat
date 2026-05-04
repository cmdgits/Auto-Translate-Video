@echo off
setlocal
cd /d "%~dp0"
"%~dp0tools\Python312\python.exe" -m app.main worker
