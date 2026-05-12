@echo off
chcp 65001 >nul
title 🗑️ Xóa lịch tự động

set TASK_NAME=FootballAutoPostXiata

echo Đang xóa lịch tự động đăng bài...
schtasks /delete /tn "%TASK_NAME%_7h" /f
schtasks /delete /tn "%TASK_NAME%_13h" /f
schtasks /delete /tn "%TASK_NAME%_20h" /f

echo ✅ Đã xóa xong!
pause
