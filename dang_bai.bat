@echo off
chcp 65001 >nul
title ⚽ Football Auto Poster - Xiata

echo.
echo ╔══════════════════════════════════════════════════╗
echo ║   ⚽ HỆ THỐNG TỰ ĐỘNG ĐĂNG BÀI BÓNG ĐÁ ⚽    ║
echo ║                  by Xiata                        ║
echo ╚══════════════════════════════════════════════════╝
echo.

:: Chuyển đến thư mục chứa script
cd /d "%~dp0"

:: Chạy PHP
C:\xampp\php\php.exe run_football_post.php

echo.
echo ✅ Hoàn thành lúc %date% %time%
echo.
