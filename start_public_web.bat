@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

set "APP_HOST=0.0.0.0"
set "APP_PORT=8080"
set "APP_LOCAL_URL=http://127.0.0.1:%APP_PORT%/"
set "PUBLIC_URL=https://capcut.hieupro.io.vn/"
set "APP_LOG=%~dp0public_web_hidden.log"
set "APP_ERR_LOG=%~dp0public_web_hidden_error.log"
set "APP_PID=%~dp0public_web_hidden.pid"
set "AUTOTRANSLATE_WORKER_BACKEND=thread"

if /i "%~1"=="ui" goto init
if /i "%~1"=="hidden" goto init
if /i "%~1"=="stop" goto stop_all_web
if /i "%~1"=="close" goto close_firewall
if /i "%~1"=="status" goto status_all

:menu
cls
echo ==========================================
echo   Auto Translate Video - Cloudflare Tunnel
echo ==========================================
echo  1. Chay co UI   - hien cua so log
echo  2. Chay an      - chay nen, khong hien log
echo  3. Dung toan bo web app dang chay
echo  4. Kiem tra trang thai
echo  5. Dong firewall port %APP_PORT%
echo  6. Thoat
echo.
echo May nay xem local: %APP_LOCAL_URL%
echo Link public: %PUBLIC_URL%
echo Cloudflare Tunnel tro ve: http://127.0.0.1:%APP_PORT%
echo.
set "CHOICE="
set /p "CHOICE=Chon 1-6: "
if "%CHOICE%"=="1" set "RUN_MODE=ui"& goto init
if "%CHOICE%"=="2" set "RUN_MODE=hidden"& goto init
if "%CHOICE%"=="3" goto stop_all_web
if "%CHOICE%"=="4" goto status_all
if "%CHOICE%"=="5" goto close_firewall
if "%CHOICE%"=="6" exit /b 0
goto menu

:init
if /i "%~1"=="ui" set "RUN_MODE=ui"
if /i "%~1"=="hidden" set "RUN_MODE=hidden"
if not defined RUN_MODE set "RUN_MODE=ui"

call :find_python
if errorlevel 1 exit /b 1
if /i "%RUN_MODE%"=="hidden" (
  call :is_running
  if "!SERVER_RUNNING!"=="1" goto run_hidden
)
call :ensure_port_free
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

:ensure_port_free
set "PORT_BUSY=0"
for /f "tokens=*" %%L in ('netstat -ano ^| findstr /C:":%APP_PORT%" ^| findstr /C:"LISTENING"') do (
  if "!PORT_BUSY!"=="0" echo [LOI] Cong %APP_PORT% dang bi chiem:
  set "PORT_BUSY=1"
  echo   %%L
)
if "%PORT_BUSY%"=="1" (
  echo Hay tat tien trinh dang chiem cong %APP_PORT% roi chay lai.
  echo Neu la web app nay, chon muc 3 de dung toan bo web app.
  pause
  exit /b 1
)
exit /b 0

:open_firewall_if_admin
net session >nul 2>nul
if not errorlevel 1 (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$port=[int]$env:APP_PORT; $rule='Auto Translate Video Public '+$port; $existing=Get-NetFirewallRule -DisplayName $rule -ErrorAction SilentlyContinue; if($existing){ Set-NetFirewallRule -DisplayName $rule -Enabled True -Profile Private,Public; Set-NetFirewallPortFilter -AssociatedNetFirewallRule $existing -Protocol TCP -LocalPort $port } else { New-NetFirewallRule -DisplayName $rule -Direction Inbound -Action Allow -Protocol TCP -LocalPort $port -Profile Private,Public | Out-Null }" >nul 2>nul
) else (
  echo [INFO] Chua chay bang Administrator nen bo qua mo Windows Firewall port %APP_PORT%.
  echo [INFO] Neu dung Cloudflare Tunnel cung may thi khong can mo firewall.
)
exit /b 0

:run_ui
echo.
echo ==========================================
echo   Auto Translate Video - Cloudflare Tunnel UI
echo ==========================================
echo Server listen: http://0.0.0.0:%APP_PORT%
echo May nay xem local: %APP_LOCAL_URL%
echo Link public: %PUBLIC_URL%
echo Cloudflare Tunnel tro ve: http://127.0.0.1:%APP_PORT%
echo Khong bat dang nhap khi truy cap web.
echo Nhan Ctrl+C de dung server.
echo.
"%PYTHON_EXE%" -m app.main web --host %APP_HOST% --port %APP_PORT% --no-open-browser
if errorlevel 1 (
  echo.
  echo [LOI] Web server bi dung hoac khong mo duoc cong %APP_PORT%.
  echo Hay kiem tra cong %APP_PORT% co bi phan mem khac chiem khong.
  pause
)
exit /b %ERRORLEVEL%

:run_hidden
if not defined PYTHON_EXE call :find_python
call :is_running
if "%SERVER_RUNNING%"=="1" (
  echo.
  echo Server an dang chay san tai port %APP_PORT%.
  echo May nay xem local: %APP_LOCAL_URL%
  echo Link public: %PUBLIC_URL%
  echo Cloudflare Tunnel tro ve: http://127.0.0.1:%APP_PORT%
  pause
  exit /b 0
)
echo.
echo Dang chay server an tai port %APP_PORT%...
echo Log: %APP_LOG%
del "%APP_LOG%" >nul 2>nul
del "%APP_ERR_LOG%" >nul 2>nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$project=(Resolve-Path '.').Path; $python=$env:PYTHON_EXE; $log=$env:APP_LOG; $errLog=$env:APP_ERR_LOG; $pidFile=$env:APP_PID; $hostName=$env:APP_HOST; $port=$env:APP_PORT; $args=@('-m','app.main','web','--host',$hostName,'--port',$port,'--no-open-browser'); $process=Start-Process -FilePath $python -ArgumentList $args -WorkingDirectory $project -WindowStyle Hidden -RedirectStandardOutput $log -RedirectStandardError $errLog -PassThru; Set-Content -Path $pidFile -Value $process.Id -Encoding ASCII"
if errorlevel 1 (
  echo [LOI] Khong the chay an server. Hay thu chon 1 de xem loi.
  pause
  exit /b 1
)
set "SERVER_STARTED=0"
set "START_TRIES=0"

:wait_hidden_start
set /a START_TRIES+=1
ping -n 2 127.0.0.1 >nul
call :is_running
if "%SERVER_RUNNING%"=="1" set "SERVER_STARTED=1"& goto hidden_started
if %START_TRIES% LSS 10 goto wait_hidden_start

:hidden_started
if "%SERVER_STARTED%"=="1" (
  echo Server da chay an.
  echo May nay xem local: %APP_LOCAL_URL%
  echo Link public: %PUBLIC_URL%
  echo Cloudflare Tunnel tro ve: http://127.0.0.1:%APP_PORT%
) else (
  echo [LOI] Server vua tat sau khi chay an. Xem log loi:
  echo %APP_ERR_LOG%
)
pause
exit /b 0

:is_running
set "SERVER_RUNNING=0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; try{ $response=Invoke-WebRequest -UseBasicParsing -Uri $env:APP_LOCAL_URL -TimeoutSec 5; if($response.StatusCode -eq 200 -and $response.Content -like '*Auto Translate Video*'){ exit 0 } } catch{}; exit 1" >nul 2>nul
if not errorlevel 1 set "SERVER_RUNNING=1"
exit /b 0

:stop_all_web
echo.
echo Dang dung toan bo tien trinh Python dang chay website nay...
set "STOP_FOUND=0"
set "STOP_FAILED=0"
set "PID_VALUE="
if exist "%APP_PID%" set /p "PID_VALUE="<"%APP_PID%"
if defined PID_VALUE (
  set "STOP_FOUND=1"
  taskkill /PID !PID_VALUE! /T /F >nul 2>nul
  if errorlevel 1 (
    ping -n 2 127.0.0.1 >nul
    tasklist /FI "PID eq !PID_VALUE!" /NH | findstr /I /C:"python.exe" /C:"pythonw.exe" >nul 2>nul
    if errorlevel 1 (echo PID !PID_VALUE! da tat) else (set "STOP_FAILED=1"& echo Khong dung duoc PID !PID_VALUE!)
  ) else echo Da dung PID !PID_VALUE!
)
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /C:":%APP_PORT%" ^| findstr /C:"LISTENING"') do (
  if "%%P"=="!PID_VALUE!" (
    rem PID nay da duoc yeu cau dung o tren.
  ) else (
    tasklist /FI "PID eq %%P" /NH | findstr /I /C:"python.exe" /C:"pythonw.exe" >nul 2>nul
    if not errorlevel 1 (
      set "STOP_FOUND=1"
      taskkill /PID %%P /T /F >nul 2>nul
      if errorlevel 1 (
        ping -n 2 127.0.0.1 >nul
        tasklist /FI "PID eq %%P" /NH | findstr /I /C:"python.exe" /C:"pythonw.exe" >nul 2>nul
        if errorlevel 1 (echo PID %%P da tat) else (set "STOP_FAILED=1"& echo Khong dung duoc PID %%P)
      ) else echo Da dung PID %%P
    ) else (
      echo Port %APP_PORT% dang bi PID %%P giu nhung khong phai Python, khong tu dung.
    )
  )
)
del "%APP_PID%" >nul 2>nul
call :wait_until_stopped
if "%WAIT_STOPPED%"=="1" set "STOP_FAILED=0"
if "%WAIT_STOPPED%"=="0" if "%STOP_FOUND%"=="1" set "STOP_FAILED=1"
if "%STOP_FOUND%"=="0" echo Khong tim thay tien trinh Python web app nao de dung.
if "%STOP_FAILED%"=="1" (
  echo [CANH BAO] Co tien trinh khong dung duoc. Hay Run as administrator roi chon lai muc 3.
) else (
  echo Da xu ly lenh dung toan bo web app.
)
pause
exit /b 0

:wait_until_stopped
set "WAIT_STOPPED=0"
set "STOP_WAIT_TRIES=0"

:wait_stop_loop
set /a STOP_WAIT_TRIES+=1
ping -n 2 127.0.0.1 >nul
call :is_running
if "%SERVER_RUNNING%"=="0" set "WAIT_STOPPED=1"& exit /b 0
if %STOP_WAIT_TRIES% LSS 8 goto wait_stop_loop
exit /b 0

:status_all
echo.
echo Trang thai:
call :is_running
if "%SERVER_RUNNING%"=="1" (echo - App: dang chay %APP_LOCAL_URL%) else (echo - App: chua chay)
echo.
echo Port %APP_PORT% dang lang nghe:
set "PORT_BUSY=0"
for /f "tokens=*" %%L in ('netstat -ano ^| findstr /C:":%APP_PORT%" ^| findstr /C:"LISTENING"') do (
  set "PORT_BUSY=1"
  echo   %%L
)
if "%PORT_BUSY%"=="0" echo   Khong co tien trinh nao lang nghe port %APP_PORT%
pause
exit /b 0

:close_firewall
net session >nul 2>nul
if errorlevel 1 (
  echo [LOI] Hay chay bang Run as administrator de dong Windows Firewall port %APP_PORT%.
  pause
  exit /b 1
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$port=[int]$env:APP_PORT; $rule='Auto Translate Video Public '+$port; $existing=Get-NetFirewallRule -DisplayName $rule -ErrorAction SilentlyContinue; if($existing){ Disable-NetFirewallRule -DisplayName $rule; Write-Host ('Da dong firewall port '+$port+'.') } else { Write-Host ('Khong thay firewall rule port '+$port+'.') }"
pause
exit /b 0
