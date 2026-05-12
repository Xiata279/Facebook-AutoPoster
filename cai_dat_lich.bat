@echo off
chcp 65001 >nul
title ⚙️ Cài đặt tự động đăng bài - Xiata

cd /d "%~dp0"

echo.
echo ╔══════════════════════════════════════════════════╗
echo ║    ⚙️  CÀI ĐẶT TỰ ĐỘNG ĐĂNG BÀI BÓNG ĐÁ       ║
echo ╚══════════════════════════════════════════════════╝
echo.

:: Đường dẫn đầy đủ đến PHP và script
set PHP_PATH=C:\xampp\php\php.exe
set SCRIPT_PATH=%~dp0run_football_post.php
set TASK_NAME=FootballAutoPostXiata

echo [1] Xóa task cũ nếu có...
schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1

echo [2] Tạo task mới - đăng bài 3 lần/ngày (7h, 13h, 20h)...

:: Tạo 3 task riêng biệt cho 3 khung giờ
schtasks /create /tn "%TASK_NAME%_7h" ^
    /tr "\"%PHP_PATH%\" \"%SCRIPT_PATH%\"" ^
    /sc DAILY /st 07:00 ^
    /rl HIGHEST /f

schtasks /create /tn "%TASK_NAME%_13h" ^
    /tr "\"%PHP_PATH%\" \"%SCRIPT_PATH%\"" ^
    /sc DAILY /st 13:00 ^
    /rl HIGHEST /f

schtasks /create /tn "%TASK_NAME%_20h" ^
    /tr "\"%PHP_PATH%\" \"%SCRIPT_PATH%\"" ^
    /sc DAILY /st 20:00 ^
    /rl HIGHEST /f

echo.
echo ✅ Đã cài đặt xong! Lịch đăng bài:
echo    🕖 07:00 - Buổi sáng
echo    🕑 13:00 - Buổi trưa
echo    🕗 20:00 - Buổi tối
echo.
echo Để xem lịch: schtasks /query /tn "%TASK_NAME%*"
echo Để xóa lịch: chạy file bo_lich.bat
echo.
pause
