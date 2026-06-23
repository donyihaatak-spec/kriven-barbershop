# KRIVEN BARBERS — бот записи + Mini App

Telegram-бот с онлайн-записью для барбершопа: календарь, услуги, предоплата по СБП, админ-панель.

**Демо:** https://t.me/kriventestbot

---

## Возможности

- Mini App внутри Telegram (запись в 4 шага)
- Календарь и свободные слоты
- Прайс: стрижки + борода
- Предоплата: код `KRV-XXXX`, перевод на номер, подтверждение админом
- Вкладка «Мои записи» + отмена клиентом
- Автообновление экрана после подтверждения оплаты
- Напоминание накануне записи (в Telegram)
- Админ: кнопки в боте + веб-панель `/admin`

---

## Деплой на Render (бесплатно)

1. [render.com](https://render.com) → **New** → **Blueprint** → репозиторий `kriven-barbershop`
2. В **Environment** задать:
   - `BOT_TOKEN` — от [@BotFather](https://t.me/BotFather)
   - `ADMIN_CHAT_ID` — твой Telegram ID ([@userinfobot](https://t.me/userinfobot))
   - `ADMIN_PASSWORD` — пароль для `/admin`
   - `PREPAY_PHONE` — номер для СБП
3. **Deploy** → подождать 3–5 минут
4. В BotFather: **Bot Settings** → **Menu Button** → URL = `https://твой-сервис.onrender.com`
5. UptimeRobot: пинг `https://твой-сервис.onrender.com/health` каждые 5 мин (чтобы не засыпал)

> **Важно:** на бесплатном Render база SQLite может сброситься при редеплое. Для продакшена — платный диск или внешняя БД.

---

## Локальный запуск

```bash
pip install -r requirements.txt
cp .env.example .env   # заполни переменные
python run.py
```

Не запускай `run.py` одновременно с Render — сломается webhook.

---

## Настройка под салон

| Что менять | Файл |
|---|---|
| Название, тексты | `branding.py` |
| Прайс услуг | `catalog.py` |
| Часы, выходные, слоты | `config.py` |
| Предоплата %, номер | `.env` / Render env |
| Стили Mini App | `mini-app/style.css` |

Подробная инструкция для заказчика: [docs/HANDOFF.md](docs/HANDOFF.md)

---

## Админ

- **Telegram:** уведомления с кнопками «Оплата получена» / «Отменить»
- **Команда** `/admin` — ссылка на панель
- **Веб:** `https://твой-сервис.onrender.com/admin`

---

## Структура

```
app.py              — Render (webhook + сервер)
bot.py / run.py     — локальная разработка
handlers.py         — логика бота
server.py           — API Mini App
booking_service.py  — бизнес-логика
database.py         — SQLite
mini-app/           — фронт Mini App
admin-panel/        — веб-админка
kwork/              — тексты для Kwork
assets/             — аватар бота
```

---

## Kwork

Тексты объявлений: папка `kwork/`  
Скрины для галереи: `kwork/gallery/`
