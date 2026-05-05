@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"

set "ROOT=%~dp0"
set "TOOLS_DIR=%ROOT%tools"
set "PYTHON_DIR=%TOOLS_DIR%\Python312"
set "PYTHON_EXE=%PYTHON_DIR%\python.exe"
set "PYTHON_VERSION=3.12.10"
set "PYTHON_INSTALLER=%TOOLS_DIR%\python-%PYTHON_VERSION%-amd64.exe"
set "PYTHON_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/python-%PYTHON_VERSION%-amd64.exe"
set "FFMPEG_DIR=%TOOLS_DIR%\ffmpeg"
set "FFMPEG_BIN=%FFMPEG_DIR%\bin\ffmpeg.exe"
set "FFPROBE_BIN=%FFMPEG_DIR%\bin\ffprobe.exe"
set "FFMPEG_ZIP=%TOOLS_DIR%\ffmpeg-release-essentials.zip"
set "FFMPEG_URL=https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

if /I "%~1"=="--verify-only" (
  call :verify_install
  exit /b !errorlevel!
)

echo ============================================================
echo  Auto Translate Video - cai dat moi truong portable
echo ============================================================
echo Thu muc du an: %ROOT%
echo.

if not exist "%TOOLS_DIR%" mkdir "%TOOLS_DIR%"

call :ensure_powershell || goto :failed
call :ensure_python || goto :failed
call :ensure_pip || goto :failed
call :install_dependencies || goto :failed
call :ensure_ffmpeg || goto :failed
call :ensure_config || goto :failed
call :ensure_asr_model
call :verify_install || goto :failed

echo.
echo ============================================================
echo  Hoan tat cai dat.
echo ============================================================
echo De chay phan mem: bam dup run_web.bat
echo Sau do mo: http://127.0.0.1:8001/
echo.
echo Muon chuyen sang may khac:
echo  1. Copy ca thu muc Auto-Translate-Video sang may moi.
echo  2. Chay install_all.bat tren may moi neu thieu moi truong.
echo  3. Chay run_web.bat de su dung.
echo.
pause
exit /b 0

:ensure_powershell
where powershell.exe >nul 2>nul
if errorlevel 1 (
  echo [LOI] Khong tim thay powershell.exe. Windows can PowerShell de tai Python/FFmpeg.
  exit /b 1
)
exit /b 0

:ensure_python
if exist "%PYTHON_EXE%" (
  echo [OK] Da co Python portable: %PYTHON_EXE%
  exit /b 0
)

echo [1/6] Chua co Python portable, dang tai Python %PYTHON_VERSION%...
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_INSTALLER%'"
if errorlevel 1 (
  echo [LOI] Khong tai duoc Python. Hay kiem tra internet/firewall roi chay lai.
  exit /b 1
)

echo [1/6] Dang cai Python vao tools\Python312, khong can quyen admin...
start /wait "" "%PYTHON_INSTALLER%" /quiet InstallAllUsers=0 TargetDir="%PYTHON_DIR%" Include_pip=1 Include_launcher=0 PrependPath=0 Shortcuts=0 Include_test=0
if not exist "%PYTHON_EXE%" (
  echo [LOI] Cai Python that bai, khong tim thay %PYTHON_EXE%.
  exit /b 1
)
echo [OK] Da cai Python portable.
exit /b 0

:ensure_pip
echo [2/6] Kiem tra pip...
"%PYTHON_EXE%" -m ensurepip --upgrade >nul 2>nul
"%PYTHON_EXE%" -m pip --version >nul 2>nul
if errorlevel 1 (
  echo [LOI] Python chua co pip. Hay cai lai Python hoac kiem tra antivirus.
  exit /b 1
)
exit /b 0

:install_dependencies
echo [3/6] Cai thu vien Python can thiet...
"%PYTHON_EXE%" -m pip install --upgrade pip setuptools wheel
if errorlevel 1 exit /b 1
"%PYTHON_EXE%" -m pip install -e .
if errorlevel 1 exit /b 1
"%PYTHON_EXE%" -m pip install pyinstaller
if errorlevel 1 exit /b 1
echo [OK] Da cai dependencies.
exit /b 0

:ensure_ffmpeg
if exist "%FFMPEG_BIN%" if exist "%FFPROBE_BIN%" (
  echo [OK] Da co FFmpeg portable: tools\ffmpeg\bin
  exit /b 0
)

echo [4/6] Chua co FFmpeg portable, dang tai FFmpeg...
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '%FFMPEG_URL%' -OutFile '%FFMPEG_ZIP%'"
if errorlevel 1 (
  echo [LOI] Khong tai duoc FFmpeg. Hay kiem tra internet/firewall roi chay lai.
  exit /b 1
)

echo [4/6] Dang giai nen FFmpeg...
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $tools='%TOOLS_DIR%'; $zip='%FFMPEG_ZIP%'; $temp=Join-Path $tools 'ffmpeg_extract'; if(Test-Path $temp){Remove-Item -LiteralPath $temp -Recurse -Force}; New-Item -ItemType Directory -Path $temp | Out-Null; Expand-Archive -LiteralPath $zip -DestinationPath $temp -Force; $src=Get-ChildItem -LiteralPath $temp -Directory | Where-Object { Test-Path (Join-Path $_.FullName 'bin\ffmpeg.exe') } | Select-Object -First 1; if(-not $src){throw 'Khong tim thay ffmpeg.exe trong file zip'}; $dst='%FFMPEG_DIR%'; if(Test-Path $dst){Remove-Item -LiteralPath $dst -Recurse -Force}; Move-Item -LiteralPath $src.FullName -Destination $dst; Remove-Item -LiteralPath $temp -Recurse -Force"
if errorlevel 1 (
  echo [LOI] Giai nen FFmpeg that bai.
  exit /b 1
)
if not exist "%FFMPEG_BIN%" (
  echo [LOI] Khong tim thay %FFMPEG_BIN% sau khi giai nen.
  exit /b 1
)
echo [OK] Da cai FFmpeg portable.
exit /b 0

:ensure_config
echo [5/6] Tao/cap nhat config.yaml...
if not exist "%ROOT%config.yaml" copy /Y "%ROOT%config.example.yaml" "%ROOT%config.yaml" >nul
if not exist "%ROOT%.env" if exist "%ROOT%.env.example" copy /Y "%ROOT%.env.example" "%ROOT%.env" >nul
"%PYTHON_EXE%" -c "from pathlib import Path; import yaml; p=Path('config.yaml'); data=yaml.safe_load(p.read_text(encoding='utf-8')) or {}; data['ffmpeg_bin']='tools/ffmpeg/bin/ffmpeg.exe'; data['ffprobe_bin']='tools/ffmpeg/bin/ffprobe.exe'; data.setdefault('worker',{})['backend']='thread'; data.setdefault('asr',{})['device']='auto'; data.setdefault('asr',{})['compute_type']='auto'; p.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding='utf-8')"
if errorlevel 1 exit /b 1
if not exist "%ROOT%workspace_data" mkdir "%ROOT%workspace_data"
if not exist "%ROOT%workspace_data\jobs" mkdir "%ROOT%workspace_data\jobs"
if not exist "%ROOT%workspace_data\uploads" mkdir "%ROOT%workspace_data\uploads"
if not exist "%ROOT%workspace_data\tmp" mkdir "%ROOT%workspace_data\tmp"
echo [OK] Da cap nhat config.yaml.
exit /b 0

:ensure_asr_model
echo [6/6] Kiem tra model ASR local...
if exist "%ROOT%models\faster-whisper-tiny\model.bin" (
  echo [OK] Da co model faster-whisper-tiny local.
  exit /b 0
)
echo [6/6] Chua co model local, dang tai faster-whisper-tiny de tranh ket luc tao tac vu dau tien...
set "HF_HUB_DISABLE_XET=1"
"%PYTHON_EXE%" -c "from pathlib import Path; from huggingface_hub import snapshot_download; target=Path('models/faster-whisper-tiny'); target.mkdir(parents=True, exist_ok=True); snapshot_download(repo_id='Systran/faster-whisper-tiny', local_dir=str(target), local_dir_use_symlinks=False, allow_patterns=['config.json','model.bin','tokenizer.json','vocabulary.txt']); print('model ok:', target.resolve())"
if errorlevel 1 (
  echo [CANH BAO] Khong tai duoc model ASR local. Phan mem van chay, nhung tac vu dau tien co the phai tai model va lau hon.
  exit /b 0
)
echo [OK] Da tai model ASR local.
exit /b 0

:verify_install
echo.
echo Dang kiem tra cai dat...
"%PYTHON_EXE%" -B -c "from app.config import AppConfig; import fastapi, faster_whisper; cfg=AppConfig.load(); print('python ok'); print('ffmpeg=', cfg.ffmpeg_bin); print('worker=', cfg.worker.backend)"
if errorlevel 1 exit /b 1
"%FFMPEG_BIN%" -version >nul 2>nul
if errorlevel 1 (
  echo [LOI] FFmpeg khong chay duoc.
  exit /b 1
)
echo [OK] Kiem tra thanh cong.
exit /b 0

:failed
echo.
echo ============================================================
echo  Cai dat that bai.
echo ============================================================
echo Hay xem loi phia tren. Neu loi tai file, kiem tra internet/firewall roi chay lai install_all.bat.
echo.
pause
exit /b 1
