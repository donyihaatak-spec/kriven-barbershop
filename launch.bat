@echo off
title KRIVEN Launcher
cd /d "%~dp0"
echo.
echo Запускаю бота и туннель в двух окнах...
echo НЕ ЗАКРЫВАЙ эти окна!
echo.
start "KRIVEN Bot" cmd /k start.bat
timeout /t 4 /nobreak >nul
start "KRIVEN Tunnel" cmd /k tunnel.bat
echo.
echo Готово! Дождись ссылки в окне Tunnel,
echo вставь ее в .env как WEBAPP_URL и перезапусти Bot.
pause
