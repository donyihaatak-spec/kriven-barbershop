# KRIVEN BARBERS — Telegram-бот + Mini App

Портфолио-проект: онлайн-запись для барбершопа в Telegram.  
Бот, Mini App, предоплата по СБП, веб-админка.

**Демо:** https://t.me/kriventestbot  
**Live:** https://kriven-barbershop.onrender.com

---

## Скриншоты

### Mini App (клиент)

| Выбор услуги | Календарь | Итого |
|:---:|:---:|:---:|
| ![Выбор](kwork/gallery/00-choice.png) | ![Календарь](kwork/gallery/01-calendar.png) | ![Итого](kwork/gallery/02-summary.png) |

| Ожидание оплаты | Подтверждено |
|:---:|:---:|
| ![Оплата](kwork/gallery/03-payment.png) | ![Подтверждено](kwork/gallery/04-confirmed.png) |

### Админ-панель

| Записи | Услуги и цены |
|:---:|:---:|
| ![Админ](kwork/gallery/05-admin.png) | ![Услуги](kwork/gallery/06-services.png) |

---

## Как пользоваться

### Клиенту

1. Открой бота: https://t.me/kriventestbot
2. Нажми **Start**, затем **Записаться** (кнопка меню или в чате)
3. Выбери **Стрижка** или **Борода**
4. Выбери дату → время → вариант услуги
5. Нажми **Записаться** — появится код предоплаты `KRV-XXXX`
6. Переведи сумму на номер из экрана, в комментарии укажи код
7. После подтверждения админом экран обновится сам

**Мои записи** — вкладка внизу Mini App: статус, отмена записи.

### Администратору

**В Telegram**

- На новую запись приходит уведомление с кнопками **Оплата получена** / **Отменить**
- Команда `/admin` — ссылка на веб-панель

**В браузере**

1. Открой `https://kriven-barbershop.onrender.com/admin` (или свой URL)
2. Введи пароль (`ADMIN_PASSWORD` из настроек сервера)
3. Разделы:
   - **Бронирования** — подтверждение и отмена
   - **Услуги** — названия и цены
   - **Настройки** — часы, выходные, СБП, предоплата %
   - **Отзывы / Галерея** — контент для бота

Подробнее для заказчика: [docs/HANDOFF.md](docs/HANDOFF.md)

---

## Возможности

- Mini App внутри Telegram (запись за несколько шагов)
- Выбор **стрижки или бороды** (не оба сразу)
- Календарь и свободные слоты
- Предоплата: код `KRV-XXXX`, перевод на СБП, подтверждение админом
- «Мои записи» + отмена клиентом
- Автообновление экрана после подтверждения оплаты
- Напоминание накануне визита
- Админка в браузере — цены и настройки без программиста

---

## Стек

| Слой | Технологии |
|------|------------|
| Бот | Python, python-telegram-bot |
| Сервер / API | aiohttp |
| Mini App | HTML, CSS, JavaScript |
| База | SQLite |
| Деплой | Render |

---

## Быстрый старт (локально)

```bash
git clone https://github.com/donyihaatak-spec/kriven-barbershop.git
cd kriven-barbershop
pip install -r requirements.txt
cp .env.example .env   # заполни переменные
python run.py
```

Переменные в `.env`:

| Переменная | Описание |
|------------|----------|
| `BOT_TOKEN` | Токен от [@BotFather](https://t.me/BotFather) |
| `ADMIN_CHAT_ID` | Твой Telegram ID ([@userinfobot](https://t.me/userinfobot)) |
| `ADMIN_PASSWORD` | Пароль для `/admin` |
| `PREPAY_PHONE` | Номер для СБП |
| `WEBAPP_URL` | URL сервера (для локалки — ngrok или туннель) |

> Не запускай `run.py` одновременно с Render — сломается webhook.

---

## Деплой на Render

1. [render.com](https://render.com) → **New** → **Blueprint** → репозиторий `kriven-barbershop`
2. В **Environment** задать переменные из таблицы выше
3. **Deploy** → подождать 3–5 минут
4. В BotFather: **Bot Settings** → **Menu Button** → URL = `https://твой-сервис.onrender.com`
5. UptimeRobot: пинг `/health` каждые 5 мин (чтобы сервер не засыпал)

> На бесплатном Render SQLite может сброситься при редеплое. Для продакшена — платный диск или PostgreSQL.

---

## Структура проекта

```
app.py              — Render (webhook + HTTP-сервер)
handlers.py         — логика бота
server.py           — API Mini App
booking_service.py  — бизнес-логика записи
catalog_store.py    — услуги и цены (БД)
settings_store.py   — настройки салона (БД)
mini-app/           — фронт Mini App
admin-panel/        — веб-админка
kwork/gallery/      — скриншоты для портфолио
docs/HANDOFF.md     — инструкция для владельца салона
```

---

## Переснять скриншоты

```bash
python scripts/capture_gallery.py
```

Сохраняет PNG в `kwork/gallery/`.

---

## Kwork / портфолио

- Тексты объявлений: `kwork/`
- Брендинг: `kwork/bonnement/`
- Скрины: `kwork/gallery/`

---

## Автор

**bonnement** — Telegram-боты, Mini App, Python.  
Демо этого проекта: [@kriventestbot](https://t.me/kriventestbot)
