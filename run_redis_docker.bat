@echo off
setlocal
cd /d "%~dp0"

where docker >nul 2>nul
if errorlevel 1 (
  echo Khong tim thay Docker trong PATH.
  echo Hay cai Docker Desktop hoac cai Redis rieng, sau do chay Redis tai localhost:6379.
  pause
  exit /b 1
)

docker start auto-translate-redis >nul 2>nul
if not errorlevel 1 (
  echo Redis container auto-translate-redis da duoc bat lai tai localhost:6379.
  pause
  exit /b 0
)

docker run --name auto-translate-redis -p 6379:6379 -d redis:7-alpine
if errorlevel 1 (
  echo Khong the tao Redis container. Hay kiem tra Docker Desktop da chay chua.
  pause
  exit /b 1
)

echo Redis da chay tai localhost:6379.
pause
