@echo off
title KRIVEN - Deploy helper
cd /d "%~dp0"
echo.
echo === Деплой на Render (бесплатно) ===
echo.
echo 1. Зарегистрируйся: https://render.com
echo 2. Создай репозиторий на GitHub и залей этот проект
echo 3. На Render: New - Blueprint - подключи репозиторий
echo 4. Добавь переменные BOT_TOKEN и ADMIN_CHAT_ID
echo 5. Deploy - получишь постоянную ссылку https://xxx.onrender.com
echo.
echo Локально для теста хостинга: python app.py
echo.
pause
