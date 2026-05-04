@echo off
chcp 65001 >nul
echo ============================================
echo   CÀI ĐẶT OLLAMA - DỊCH VIDEO OFFLINE
echo ============================================
echo.

:: Kiểm tra Ollama đã cài chưa
where ollama >nul 2>&1
if %errorlevel%==0 (
    echo [OK] Ollama đã được cài đặt rồi!
    goto :pull_model
)

:: Tải Ollama
echo [1/3] Đang tải Ollama Setup (~300MB)...
echo      Vui lòng chờ, tốc độ phụ thuộc vào mạng của bạn...
curl -L -o "%TEMP%\OllamaSetup.exe" https://ollama.com/download/OllamaSetup.exe
if %errorlevel% neq 0 (
    echo [LOI] Không tải được Ollama. Kiểm tra kết nối mạng.
    pause
    exit /b 1
)

:: Cài đặt Ollama
echo [2/3] Đang cài đặt Ollama (tự động)...
"%TEMP%\OllamaSetup.exe" /VERYSILENT /NORESTART
echo      Đợi 10 giây để Ollama khởi động...
timeout /t 10 /nobreak >nul

:pull_model
:: Tải model AI về máy
echo [3/3] Đang tải model AI qwen2.5:3b (~1.9GB)...
echo      Đây là bước lâu nhất, vui lòng kiên nhẫn chờ...
ollama pull qwen2.5:3b
if %errorlevel% neq 0 (
    echo [LOI] Không tải được model. Hãy thử chạy lại script này.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   CÀI ĐẶT HOÀN TẤT!
echo ============================================
echo.
echo Bạn có thể đóng cửa sổ này.
echo Sau đó mở run_web.bat để bắt đầu dịch video offline.
echo.
pause
