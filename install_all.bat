@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"

set "ROOT=%~dp0"
set "TOOLS_DIR=%ROOT%tools"
set "PYTHON_DIR=%TOOLS_DIR%\Python312"
set "PYTHON_EXE=%PYTHON_DIR%\python.exe"
set "VENV_PYTHON_EXE=%PYTHON_DIR%\Scripts\python.exe"
set "PYTHON_VERSION=3.12.10"
set "PYTHON_INSTALLER=%TOOLS_DIR%\python-%PYTHON_VERSION%-amd64.exe"
set "PYTHON_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/python-%PYTHON_VERSION%-amd64.exe"
set "FFMPEG_DIR=%TOOLS_DIR%\ffmpeg"
set "FFMPEG_BIN=%FFMPEG_DIR%\bin\ffmpeg.exe"
set "FFPROBE_BIN=%FFMPEG_DIR%\bin\ffprobe.exe"
set "FFMPEG_ZIP=%TOOLS_DIR%\ffmpeg-release-essentials.zip"
set "FFMPEG_URL=https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
set "TESSERACT_VERSION=5.4.0.20240606"
set "TESSERACT_DIR=%TOOLS_DIR%\Tesseract-OCR"
set "TESSERACT_EXE=%TESSERACT_DIR%\tesseract.exe"
set "TESSERACT_INSTALLER=%TOOLS_DIR%\tesseract-ocr-w64-setup-%TESSERACT_VERSION%.exe"
set "TESSERACT_URL=https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-%TESSERACT_VERSION%.exe"
set "TESSDATA_DIR=%TESSERACT_DIR%\tessdata"

call :resolve_python_exe >nul 2>nul

if /I "%~1"=="--verify-only" (
  call :verify_install
  exit /b !errorlevel!
)
if /I "%~1"=="--install-tesseract-only" (
  if not exist "%TOOLS_DIR%" mkdir "%TOOLS_DIR%"
  call :ensure_powershell || goto :failed
  call :ensure_tesseract || goto :failed
  echo.
  echo [OK] Da cai/cau hinh Tesseract OCR cho OCR Gaussian Blur.
  exit /b 0
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
call :ensure_tesseract || goto :failed
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
call :resolve_python_exe
if exist "%PYTHON_EXE%" (
  echo [OK] Da co Python local: %PYTHON_EXE%
  exit /b 0
)

echo [1/6] Chua co Python portable, dang tai Python %PYTHON_VERSION%...
echo       Neu mang chan python.org, co the tai tay file nay vao tools:
echo       %PYTHON_URL%
call :download_file "%PYTHON_URL%" "%PYTHON_INSTALLER%"
if errorlevel 1 (
  echo [CANH BAO] Khong tai duoc Python portable tu python.org.
  echo [1/6] Thu dung Python da cai san tren may de tao moi truong local...
  call :create_venv_from_system_python
  exit /b !errorlevel!
)

echo [1/6] Dang cai Python vao tools\Python312, khong can quyen admin...
start /wait "" "%PYTHON_INSTALLER%" /quiet InstallAllUsers=0 TargetDir="%PYTHON_DIR%" Include_pip=1 Include_launcher=0 PrependPath=0 Shortcuts=0 Include_test=0
if not exist "%PYTHON_EXE%" (
  echo [CANH BAO] Cai Python portable that bai, thu tao venv bang Python da cai san...
  call :create_venv_from_system_python
  exit /b !errorlevel!
)
echo [OK] Da cai Python portable.
exit /b 0

:resolve_python_exe
if exist "%PYTHON_DIR%\python.exe" (
  set "PYTHON_EXE=%PYTHON_DIR%\python.exe"
  exit /b 0
)
if exist "%VENV_PYTHON_EXE%" (
  set "PYTHON_EXE=%VENV_PYTHON_EXE%"
  exit /b 0
)
exit /b 1

:download_file
set "DOWNLOAD_URL=%~1"
set "DOWNLOAD_OUT=%~2"
if exist "%DOWNLOAD_OUT%" (
  echo [OK] Da co file tai ve: %DOWNLOAD_OUT%
  exit /b 0
)

where curl.exe >nul 2>nul
if not errorlevel 1 (
  echo       Dang tai bang curl, co hien tien trinh...
  curl.exe -L --fail --connect-timeout 20 --max-time 600 --retry 2 --retry-delay 5 -o "%DOWNLOAD_OUT%" "%DOWNLOAD_URL%"
  if not errorlevel 1 exit /b 0
  echo [CANH BAO] curl khong tai duoc, thu PowerShell...
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; $url='%DOWNLOAD_URL%'; $out='%DOWNLOAD_OUT%'; $job=Start-Job -ScriptBlock { param($u,$o) $ProgressPreference='Continue'; Invoke-WebRequest -Uri $u -OutFile $o -UseBasicParsing } -ArgumentList $url,$out; if(Wait-Job $job -Timeout 600){ Receive-Job $job -ErrorAction Stop } else { Stop-Job $job -Force; throw 'Qua thoi gian tai file 10 phut' }"
exit /b %errorlevel%

:create_venv_from_system_python
set "SYSTEM_PYTHON="
py -3.12 -c "import sys; sys.exit(0 if (3,11) <= sys.version_info[:2] < (3,15) else 1)" >nul 2>nul
if not errorlevel 1 set "SYSTEM_PYTHON=py -3.12"
if not defined SYSTEM_PYTHON (
  py -3 -c "import sys; sys.exit(0 if (3,11) <= sys.version_info[:2] < (3,15) else 1)" >nul 2>nul
  if not errorlevel 1 set "SYSTEM_PYTHON=py -3"
)
if not defined SYSTEM_PYTHON (
  python -c "import sys; sys.exit(0 if (3,11) <= sys.version_info[:2] < (3,15) else 1)" >nul 2>nul
  if not errorlevel 1 set "SYSTEM_PYTHON=python"
)
if not defined SYSTEM_PYTHON (
  echo [LOI] Khong tai duoc Python va may cung chua co Python 3.11-3.14.
  echo       Cach xu ly nhanh: cai Python 3.12 tu https://www.python.org/downloads/windows/
  echo       Sau do chay lai install_all.bat.
  exit /b 1
)
echo [OK] Tim thay Python he thong: %SYSTEM_PYTHON%
if exist "%PYTHON_DIR%" if not exist "%PYTHON_EXE%" if not exist "%VENV_PYTHON_EXE%" (
  echo       Xoa thu muc Python312 loi/khong day du de tao moi truong moi...
  rmdir /s /q "%PYTHON_DIR%"
)
%SYSTEM_PYTHON% -m venv "%PYTHON_DIR%"
if errorlevel 1 (
  echo [LOI] Khong tao duoc moi truong Python local bang venv.
  exit /b 1
)
call :resolve_python_exe
if not exist "%PYTHON_EXE%" (
  echo [LOI] Tao venv xong nhung khong tim thay Python local.
  exit /b 1
)
echo [OK] Da tao Python local: %PYTHON_EXE%
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

:ensure_tesseract
echo [3b/6] Kiem tra Tesseract OCR...
if exist "%TESSERACT_EXE%" (
  echo [OK] Da co Tesseract OCR portable: %TESSERACT_EXE%
  call :ensure_tesseract_languages
  exit /b 0
)
where tesseract.exe >nul 2>nul
if not errorlevel 1 (
  echo [OK] Da co Tesseract OCR trong PATH.
  exit /b 0
)
if exist "%ProgramFiles%\Tesseract-OCR\tesseract.exe" (
  echo [OK] Da co Tesseract OCR: %ProgramFiles%\Tesseract-OCR\tesseract.exe
  call :copy_tesseract_from_system "%ProgramFiles%\Tesseract-OCR"
  call :ensure_tesseract_languages
  exit /b 0
)
echo [3b/6] Chua co Tesseract, dang tai ban portable UB Mannheim...
echo       %TESSERACT_URL%
call :download_file "%TESSERACT_URL%" "%TESSERACT_INSTALLER%"
if errorlevel 1 (
  echo [CANH BAO] Khong tai duoc Tesseract truc tiep, thu cai bang winget neu co...
  where winget.exe >nul 2>nul
  if errorlevel 1 (
    echo [LOI] Khong co winget va khong tai duoc installer Tesseract.
    echo       Hay tai tay/cai Tesseract OCR tu: https://github.com/UB-Mannheim/tesseract/wiki
    exit /b 1
  )
  winget.exe install --id UB-Mannheim.TesseractOCR --exact --silent --accept-source-agreements --accept-package-agreements
  if errorlevel 1 exit /b 1
  exit /b 0
)

echo [3b/6] Dang cai Tesseract portable vao tools\Tesseract-OCR...
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $installer='%TESSERACT_INSTALLER%'; $target='%TESSERACT_DIR%'; if(Test-Path $target){Remove-Item -LiteralPath $target -Recurse -Force}; Start-Process -FilePath $installer -ArgumentList @('/S',('/D='+$target)) -Wait"
if not exist "%TESSERACT_EXE%" if exist "%ProgramFiles%\Tesseract-OCR\tesseract.exe" (
  echo [3b/6] Installer da cai vao Program Files, dang copy ve tools\Tesseract-OCR...
  call :copy_tesseract_from_system "%ProgramFiles%\Tesseract-OCR"
)
if not exist "%TESSERACT_EXE%" (
  echo [LOI] Cai Tesseract portable that bai, khong tim thay %TESSERACT_EXE%.
  exit /b 1
)
call :ensure_tesseract_languages
echo [OK] Da cai Tesseract OCR portable.
exit /b 0

:copy_tesseract_from_system
set "TESS_SOURCE=%~1"
if exist "%TESSERACT_EXE%" exit /b 0
if not exist "%TESS_SOURCE%\tesseract.exe" exit /b 1
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $src='%TESS_SOURCE%'; $dst='%TESSERACT_DIR%'; if(Test-Path $dst){Remove-Item -LiteralPath $dst -Recurse -Force}; Copy-Item -LiteralPath $src -Destination $dst -Recurse -Force"
if errorlevel 1 exit /b 1
exit /b 0

:ensure_tesseract_languages
if not exist "%TESSDATA_DIR%" mkdir "%TESSDATA_DIR%"
call :download_tessdata eng
call :download_tessdata chi_sim
call :download_tessdata chi_tra
exit /b 0

:download_tessdata
set "TESS_LANG=%~1"
set "TESSDATA_FILE=%TESSDATA_DIR%\%TESS_LANG%.traineddata"
if exist "%TESSDATA_FILE%" (
  echo [OK] Da co tessdata %TESS_LANG%.
  exit /b 0
)
echo       Tai tessdata %TESS_LANG%...
call :download_file "https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/%TESS_LANG%.traineddata" "%TESSDATA_FILE%"
if errorlevel 1 (
  echo [CANH BAO] Khong tai duoc tessdata %TESS_LANG%. OCR ngon ngu nay co the chua chinh xac.
  exit /b 0
)
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
if exist "%TESSERACT_EXE%" (
  "%TESSERACT_EXE%" --version >nul 2>nul
  if errorlevel 1 (
    echo [CANH BAO] Tesseract portable ton tai nhung chua chay duoc: %TESSERACT_EXE%
  ) else (
    echo [OK] Tesseract OCR portable san sang.
  )
) else (
  where tesseract.exe >nul 2>nul
  if errorlevel 1 (
    echo [CANH BAO] Chua tim thay Tesseract OCR. Hay chay: install_all.bat --install-tesseract-only
  ) else (
    echo [OK] Tesseract OCR da co trong PATH.
  )
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
