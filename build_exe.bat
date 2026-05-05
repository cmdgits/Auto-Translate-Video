@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_EXE=%~dp0tools\Python312\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

echo [Auto Translate Video] Kiem tra PyInstaller...
"%PYTHON_EXE%" -m PyInstaller --version >nul 2>nul
if errorlevel 1 (
  echo.
  echo Chua co PyInstaller trong moi truong Python hien tai.
  echo Cai bang lenh sau roi chay lai file nay:
  echo "%PYTHON_EXE%" -m pip install pyinstaller
  echo.
  pause
  exit /b 1
)

echo [Auto Translate Video] Dang dong goi ban .exe...
"%PYTHON_EXE%" -m PyInstaller --noconfirm --clean packaging\AutoTranslateVideo.spec
if errorlevel 1 (
  echo.
  echo Dong goi that bai. Hay xem log loi phia tren.
  pause
  exit /b 1
)

echo.
echo Hoan tat: dist\AutoTranslateVideo\AutoTranslateVideo.exe
echo Chay file exe nay de mo web UI tai http://127.0.0.1:8001/
pause
