@echo off
title KRIVEN - Tunnel (не закрывай!)
echo.
echo ========================================
echo   KRIVEN - HTTPS туннель для Mini App
echo ========================================
echo.
echo 1. Сначала должен работать start.bat
echo 2. Оставь ЭТО окно открытым
echo 3. Скопируй ссылку https://....lhr.life
echo 4. Вставь в .env как WEBAPP_URL
echo 5. Перезапусти start.bat
echo.
ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=30 -R 80:127.0.0.1:8080 nokey@localhost.run
pause
