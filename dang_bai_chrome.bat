@echo off
chcp 65001 >nul
title ⚽ Tự động đăng bài bóng đá qua Chrome

echo.
echo ╔══════════════════════════════════════════════════╗
echo ║   ⚽ TỰ ĐỘNG ĐĂNG BÀI BÓNG ĐÁ QUA CHROME ⚽   ║
echo ║                  by Xiata                        ║
echo ╚══════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

:: ─── BƯỚC 1: Kiểm tra Chrome đang chạy chưa ───
echo [1/4] Kiểm tra Chrome remote debugging...
powershell -Command "try { $r = Invoke-WebRequest http://localhost:9222/json -TimeoutSec 2 -UseBasicParsing; Write-Host '✅ Chrome đang chạy và sẵn sàng' } catch { Write-Host '❌ Chrome chưa bật! Hãy chạy mo_chrome.bat trước.'; exit 1 }"
if %errorlevel% neq 0 (
    echo.
    echo Mở mo_chrome.bat để khởi động Chrome, sau đó chạy lại file này.
    pause & exit
)

echo.

:: ─── BƯỚC 2: PHP thu thập tin + AI tạo bài ───
echo [2/4] PHP đang thu thập tin tức và tạo bài đăng...
echo.
C:\xampp\php\php.exe run_football_post.php preview-post
echo.

:: Kiểm tra có file output không
if not exist "output\latest_post.json" (
    echo ❌ Không tìm thấy output\latest_post.json
    echo    PHP chưa tạo bài đăng. Kiểm tra lỗi ở trên.
    pause & exit
)

echo ✅ Bài đăng đã được AI tạo xong!
echo.

:: ─── BƯỚC 3: Kiểm tra Python ───
echo [3/4] Kiểm tra Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python chưa cài! Tải tại: https://python.org
    pause & exit
)

python -c "import selenium" >nul 2>&1
if %errorlevel% neq 0 (
    echo 📦 Đang cài selenium + webdriver-manager...
    pip install selenium webdriver-manager
)
echo ✅ Python và Selenium sẵn sàng
echo.

:: ─── BƯỚC 4: Python đăng lên Facebook qua Chrome ───
echo [4/4] Đang đăng bài lên Facebook qua Chrome...
echo.
python chrome_poster.py

echo.
echo ═══════════════════════════════════════
if %errorlevel%==0 (
    echo ✅ HOÀN THÀNH! Bài đã được đăng lên Facebook.
) else (
    echo ❌ Có lỗi xảy ra. Xem log tại logs\chrome_poster.log
)
echo ═══════════════════════════════════════
echo.
pause
