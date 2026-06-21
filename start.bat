@echo off
title KRIVEN Bot + Tunnel
cd /d "%~dp0"
echo.
echo  Запуск бота, сервера и HTTPS туннеля...
echo  Не закрывай это окно!
echo.
python run.py
pause
