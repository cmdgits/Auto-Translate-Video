@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

set "APP_HOST=0.0.0.0"
set "APP_PORT=80"
set "APP_LOCAL_URL=http://127.0.0.1:%APP_PORT%/"
set "APP_LOG=%~dp0public_web_hidden.log"
set "APP_ERR_LOG=%~dp0public_web_hidden_error.log"
set "APP_PID=%~dp0public_web_hidden.pid"
set "AUTOTRANSLATE_WORKER_BACKEND=thread"

if /i "%~1"=="ui" goto init
if /i "%~1"=="hidden" goto init
if /i "%~1"=="stop" goto stop_hidden
if /i "%~1"=="close" goto close_firewall

:menu
cls
echo ==========================================
echo   Auto Translate Video - Public Web
echo ==========================================
echo  1. Chay co UI   - hien cua so log
echo  2. Chay an      - chay nen, khong hien log
echo  3. Dung server an
echo  4. Dong firewall port 80
echo  5. Thoat
echo.
echo Domain nao tro A record ve IP public cua server nay deu dung duoc.
echo.
set "CHOICE="
set /p "CHOICE=Chon 1-5: "
if "%CHOICE%"=="1" set "RUN_MODE=ui"& goto init
if "%CHOICE%"=="2" set "RUN_MODE=hidden"& goto init
if "%CHOICE%"=="3" goto stop_hidden
if "%CHOICE%"=="4" goto close_firewall
if "%CHOICE%"=="5" exit /b 0
goto menu

:init
if /i "%~1"=="ui" set "RUN_MODE=ui"
if /i "%~1"=="hidden" set "RUN_MODE=hidden"
if not defined RUN_MODE set "RUN_MODE=ui"

call :find_python
if errorlevel 1 exit /b 1
call :open_firewall_if_admin

if /i "%RUN_MODE%"=="hidden" goto run_hidden
goto run_ui

:find_python
if exist "%~dp0tools\ffmpeg\bin\ffmpeg.exe" set "PATH=%~dp0tools\ffmpeg\bin;%PATH%"
set "PYTHON_EXE=%~dp0tools\Python312\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=%~dp0tools\Python312\Scripts\python.exe"
if not exist "%PYTHON_EXE%" (
  echo Khong tim thay Python local. Hay chay install_all.bat truoc.
  pause
  exit /b 1
)
exit /b 0

:open_firewall_if_admin
net session >nul 2>nul
if not errorlevel 1 (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$rule='Auto Translate Video Web Public 80'; $existing=Get-NetFirewallRule -DisplayName $rule -ErrorAction SilentlyContinue; if ($existing) { Set-NetFirewallRule -DisplayName $rule -Enabled True -Profile Private,Public; Set-NetFirewallPortFilter -AssociatedNetFirewallRule $existing -Protocol TCP -LocalPort 80 } else { New-NetFirewallRule -DisplayName $rule -Direction Inbound -Action Allow -Protocol TCP -LocalPort 80 -Profile Private,Public | Out-Null }" >nul 2>nul
) else (
  echo [CANH BAO] Chua chay bang Administrator nen khong tu mo duoc Windows Firewall.
  echo Neu ben ngoai khong vao duoc, hay bam chuot phai file nay va chon Run as administrator mot lan.
)
exit /b 0

:run_ui
echo.
echo ==========================================
echo   Auto Translate Video - Public Web UI
echo ==========================================
echo Server listen: http://0.0.0.0:%APP_PORT%
echo May nay xem local: %APP_LOCAL_URL%
echo Domain nao tro A record ve IP public cua server nay deu dung duoc.
echo Khong bat dang nhap khi truy cap web.
echo Nhan Ctrl+C de dung server.
echo.
"%PYTHON_EXE%" -m app.main web --host %APP_HOST% --port %APP_PORT% --no-open-browser
if errorlevel 1 (
  echo.
  echo [LOI] Web server bi dung hoac khong mo duoc cong %APP_PORT%.
  echo Hay kiem tra cong 80 co bi IIS/Nginx/Apache/phan mem khac chiem khong.
  pause
)
exit /b %ERRORLEVEL%

:run_hidden
call :is_running
if "%SERVER_RUNNING%"=="1" (
  echo.
  echo Server an dang chay san tai port %APP_PORT%.
  echo May nay xem local: %APP_LOCAL_URL%
  pause
  exit /b 0
)
echo.
echo Dang chay server an tai port %APP_PORT%...
echo Log: %APP_LOG%
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$project=(Resolve-Path '.').Path; $python=$env:PYTHON_EXE; $log=$env:APP_LOG; $errLog=$env:APP_ERR_LOG; $pidFile=$env:APP_PID; $hostName=$env:APP_HOST; $port=$env:APP_PORT; $args=@('-m','app.main','web','--host',$hostName,'--port',$port,'--no-open-browser'); $process=Start-Process -FilePath $python -ArgumentList $args -WorkingDirectory $project -WindowStyle Hidden -RedirectStandardOutput $log -RedirectStandardError $errLog -PassThru; Set-Content -Path $pidFile -Value $process.Id -Encoding ASCII"
if errorlevel 1 (
  echo [LOI] Khong the chay an server. Hay thu chon 1 de xem loi.
  pause
  exit /b 1
)
timeout /t 2 /nobreak >nul
call :is_running
if "%SERVER_RUNNING%"=="1" (
  echo Server da chay an.
  echo May nay xem local: %APP_LOCAL_URL%
  echo Domain nao tro A record ve IP public cua server nay deu dung duoc.
) else (
  echo [LOI] Server vua tat sau khi chay an. Xem log loi:
  echo %APP_ERR_LOG%
)
pause
exit /b 0

:stop_hidden
if not exist "%APP_PID%" (
  echo.
  echo Khong thay PID server an. Neu server van chay, hay dong python.exe trong Task Manager.
  pause
  exit /b 0
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$pidFile=$env:APP_PID; $pidValue=[int](Get-Content -Path $pidFile -ErrorAction Stop); $process=Get-Process -Id $pidValue -ErrorAction SilentlyContinue; if ($process) { Stop-Process -Id $pidValue -Force; Write-Host 'Da dung server an.' } else { Write-Host 'Server an khong con chay.' }"
del "%APP_PID%" >nul 2>nul
pause
exit /b 0

:is_running
set "SERVER_RUNNING=0"
if exist "%APP_PID%" (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$pidFile=$env:APP_PID; $pidValue=[int](Get-Content -Path $pidFile -ErrorAction Stop); if (Get-Process -Id $pidValue -ErrorAction SilentlyContinue) { exit 0 } exit 1" >nul 2>nul
  if not errorlevel 1 set "SERVER_RUNNING=1"
)
exit /b 0

:close_firewall
net session >nul 2>nul
if errorlevel 1 (
  echo [LOI] Hay chay bang Run as administrator de dong Windows Firewall port 80.
  pause
  exit /b 1
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$rule='Auto Translate Video Web Public 80'; $existing=Get-NetFirewallRule -DisplayName $rule -ErrorAction SilentlyContinue; if ($existing) { Disable-NetFirewallRule -DisplayName $rule; Write-Host 'Da dong firewall port 80.' } else { Write-Host 'Khong thay firewall rule port 80.' }"
pause
exit /b 0
