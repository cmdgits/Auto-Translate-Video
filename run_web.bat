@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "APP_HOST=127.0.0.1"
set "APP_PORT=8002"
set "APP_URL=http://%APP_HOST%:%APP_PORT%/"
set "APP_LOG=%~dp0web_hidden.log"
set "APP_ERR_LOG=%~dp0web_hidden_error.log"
set "APP_PID=%~dp0web_hidden.pid"
set "AUTOTRANSLATE_WORKER_BACKEND=thread"

if exist "%~dp0tools\ffmpeg\bin\ffmpeg.exe" set "PATH=%~dp0tools\ffmpeg\bin;%PATH%"
set "PYTHON_EXE=%~dp0tools\Python312\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=%~dp0tools\Python312\Scripts\python.exe"
if not exist "%PYTHON_EXE%" (
  echo Khong tim thay Python local. Hay chay install_all.bat truoc.
  pause
  exit /b 1
)

if /i "%~1"=="ui" goto run_ui
if /i "%~1"=="hidden" goto run_hidden
if /i "%~1"=="stop" goto stop_hidden

:menu
cls
echo ==========================================
echo    Auto Translate Video - Web Server
echo ==========================================
echo  1. Chay co UI  - hien cua so log va tu mo web
echo  2. Chay an     - chay nen, khong mo cua so log
echo  3. Dung server an
echo  4. Thoat
echo.
set "CHOICE="
set /p "CHOICE=Chon 1-4: "
if "%CHOICE%"=="1" goto run_ui
if "%CHOICE%"=="2" goto run_hidden
if "%CHOICE%"=="3" goto stop_hidden
if "%CHOICE%"=="4" exit /b 0
goto menu

:run_ui
echo.
echo Dang chay server co UI tai %APP_URL%
echo Nhan Ctrl+C de dung server.
echo.
"%PYTHON_EXE%" -m app.main web --host %APP_HOST% --port %APP_PORT% --open-browser
if errorlevel 1 (
  echo.
  echo [LOI] Server bi crash hoac tat dot ngot. Hay doc thong bao loi ben tren.
  pause
)
exit /b %ERRORLEVEL%

:run_hidden
call :is_running
if "%SERVER_RUNNING%"=="1" (
  echo.
  echo Server dang chay san o %APP_URL%
  start "" "%APP_URL%"
  pause
  exit /b 0
)
echo.
echo Dang chay server an tai %APP_URL%
echo Log: %APP_LOG%
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$project = (Resolve-Path '.').Path; $python = $env:PYTHON_EXE; $log = $env:APP_LOG; $errLog = $env:APP_ERR_LOG; $pidFile = $env:APP_PID; $hostName = $env:APP_HOST; $port = $env:APP_PORT; $args = @('-m','app.main','web','--host',$hostName,'--port',$port,'--no-open-browser'); $process = Start-Process -FilePath $python -ArgumentList $args -WorkingDirectory $project -WindowStyle Hidden -RedirectStandardOutput $log -RedirectStandardError $errLog -PassThru; Set-Content -Path $pidFile -Value $process.Id -Encoding ASCII"
if errorlevel 1 (
  echo [LOI] Khong the chay an server. Hay thu chon 1 de xem loi.
  pause
  exit /b 1
)
timeout /t 2 /nobreak >nul
echo Server da chay an. Dang mo web...
start "" "%APP_URL%"
pause
exit /b 0

:stop_hidden
if not exist "%APP_PID%" (
  echo.
  echo Khong thay PID server an. Neu server van chay, hay dong trong Task Manager.
  pause
  exit /b 0
)
set /p SERVER_PID=<"%APP_PID%"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$pidValue = [int](Get-Content -Path $env:APP_PID -ErrorAction Stop); $process = Get-Process -Id $pidValue -ErrorAction SilentlyContinue; if ($process) { Stop-Process -Id $pidValue -Force; Write-Host 'Da dung server an.' } else { Write-Host 'Server an khong con chay.' }"
del "%APP_PID%" >nul 2>nul
pause
exit /b 0

:is_running
set "SERVER_RUNNING=0"
if exist "%APP_PID%" (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$pidFile = $env:APP_PID; $pidValue = [int](Get-Content -Path $pidFile -ErrorAction Stop); if (Get-Process -Id $pidValue -ErrorAction SilentlyContinue) { exit 0 } exit 1" >nul 2>nul
  if not errorlevel 1 set "SERVER_RUNNING=1"
)
exit /b 0
