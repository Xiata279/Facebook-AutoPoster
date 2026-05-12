@echo off
chcp 65001 >nul
title 🌐 Khởi động Chrome với Remote Debugging

echo.
echo ╔══════════════════════════════════════════════════╗
echo ║   🌐 KHỞI ĐỘNG CHROME ĐỂ BOT KẾT NỐI           ║
echo ╚══════════════════════════════════════════════════╝
echo.
echo Chrome sẽ mở với cổng 9222 để bot kết nối...
echo Sau khi Chrome mở, hãy đăng nhập Facebook nếu chưa đăng nhập.
echo.

:: Tìm Chrome
set CHROME_PATH=
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    set CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe
) else if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    set CHROME_PATH=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe
) else (
    echo ❌ Không tìm thấy Chrome! Hãy kiểm tra đường dẫn.
    pause & exit
)

:: Profile riêng để không ảnh hưởng Chrome thường
set PROFILE_DIR=%~dp0chrome_profile

echo Đường dẫn Chrome: %CHROME_PATH%
echo Profile: %PROFILE_DIR%
echo.
echo 💡 Sau khi Chrome mở xong → chạy dang_bai_chrome.bat để đăng bài
echo.

start "" "%CHROME_PATH%" ^
  --remote-debugging-port=9222 ^
  --user-data-dir="%PROFILE_DIR%" ^
  --no-first-run ^
  --disable-default-apps ^
  https://www.facebook.com

echo ✅ Chrome đang khởi động...
timeout /t 3 >nul
