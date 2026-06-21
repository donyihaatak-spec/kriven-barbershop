@echo off
title KRIVEN Bot + Tunnel
cd /d "%~dp0"
echo.
echo  ============================================================
echo   ВНИМАНИЕ: бот уже на Render (kriven-barbershop.onrender.com)
echo.
echo   Для работы через интернет НЕ запускай этот файл.
echo   Открой Telegram: @kriventestbot  и  напиши /start
echo.
echo   Этот скрипт только для локальной разработки без Render.
echo  ============================================================
echo.
set /p GO="Все равно запустить локально? (y/N): "
if /I not "%GO%"=="y" exit /b 0
echo.
echo  Запуск бота, сервера и HTTPS туннеля...
echo  Не закрывай это окно!
echo.
python run.py
pause
