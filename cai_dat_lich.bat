@echo off
chcp 65001 >nul
title ⚙️ Cài Task Scheduler - Chạy với quyền Admin

echo ╔══════════════════════════════════════════════════╗
echo ║   ⚙️  CÀI ĐẶT LỊCH TỰ ĐỘNG ĐĂNG BÀI (ADMIN)   ║
echo ╚══════════════════════════════════════════════════╝
echo.

set PHP=C:\xampp\php\php.exe
set SCRIPT=C:\Users\Xiata\Desktop\facebook-auto-poster-main\facebook-auto-poster-main\run_football_post.php
set DIR=C:\Users\Xiata\Desktop\facebook-auto-poster-main\facebook-auto-poster-main

:: Xóa task cũ
schtasks /delete /tn "FootballAutoPostXiata_7h" /f 2>nul
schtasks /delete /tn "FootballAutoPostXiata_13h" /f 2>nul
schtasks /delete /tn "FootballAutoPostXiata_20h" /f 2>nul

:: Tạo task 7h sáng
schtasks /create /tn "FootballAutoPostXiata_7h" ^
  /tr "\"%PHP%\" \"%SCRIPT%\"" ^
  /sc DAILY /st 07:00 /rl HIGHEST /f /sd 05/12/2026
if %errorlevel%==0 (echo ✅ Task 7h đã tạo!) else (echo ❌ Lỗi task 7h)

:: Tạo task 13h trưa
schtasks /create /tn "FootballAutoPostXiata_13h" ^
  /tr "\"%PHP%\" \"%SCRIPT%\"" ^
  /sc DAILY /st 13:00 /rl HIGHEST /f /sd 05/12/2026
if %errorlevel%==0 (echo ✅ Task 13h đã tạo!) else (echo ❌ Lỗi task 13h)

:: Tạo task 20h tối
schtasks /create /tn "FootballAutoPostXiata_20h" ^
  /tr "\"%PHP%\" \"%SCRIPT%\"" ^
  /sc DAILY /st 20:00 /rl HIGHEST /f /sd 05/12/2026
if %errorlevel%==0 (echo ✅ Task 20h đã tạo!) else (echo ❌ Lỗi task 20h)

echo.
echo ═══════════════════════════════════════
echo  Kiểm tra lịch đã tạo:
schtasks /query /tn "FootballAutoPostXiata*" /fo LIST 2>nul
echo ═══════════════════════════════════════
echo.
echo ✅ Lịch đăng bài tự động: 7h - 13h - 20h mỗi ngày
echo.
echo ⚠️  Nhớ điền Facebook credentials vào file .env trước khi lịch chạy!
echo.
pause
