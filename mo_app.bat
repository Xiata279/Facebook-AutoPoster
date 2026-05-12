@echo off
chcp 65001 >nul
title Khởi động Football Auto Poster App

set PY=C:\Users\Xiata\AppData\Local\Programs\Python\Python312\python.exe

echo Đang kiểm tra thư viện...
"%PY%" -c "import customtkinter" >nul 2>&1
if %errorlevel% neq 0 (
    echo Đang cài customtkinter...
    "%PY%" -m pip install customtkinter pillow --quiet
)

echo Khởi động app...
"%PY%" app.py
