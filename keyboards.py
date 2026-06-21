import calendar
from datetime import date, datetime, timedelta

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from catalog import BEARD_STYLES, HAIRCUT_STYLES, MONTH_NAMES, WEEKDAY_SHORT
from config import BOOKING_DAYS_AHEAD, CLOSED_WEEKDAYS, SLOT_MINUTES, WEBAPP_URL, WORK_END_HOUR, WORK_START_HOUR
from database import is_slot_taken


def main_menu_keyboard() -> InlineKeyboardMarkup:
    if not WEBAPP_URL:
        return InlineKeyboardMarkup([])
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "◈ Записаться",
                    web_app=WebAppInfo(url=WEBAPP_URL),
                )
            ]
        ]
    )


def _date_in_range(day: date, today: date, max_date: date) -> bool:
    if day < today or day > max_date:
        return False
    if day.weekday() in CLOSED_WEEKDAYS:
        return False
    return True


def calendar_keyboard(year: int, month: int) -> InlineKeyboardMarkup:
    today = date.today()
    max_date = today + timedelta(days=BOOKING_DAYS_AHEAD)

    cal = calendar.Calendar(firstweekday=0)
    month_days = cal.monthdayscalendar(year, month)

    rows: list[list[InlineKeyboardButton]] = []

    rows.append(
        [
            InlineKeyboardButton(
                f"◈ {MONTH_NAMES[month - 1]} {year} ◈",
                callback_data="cal:ignore",
            )
        ]
    )

    rows.append(
        [InlineKeyboardButton(day, callback_data="cal:ignore") for day in WEEKDAY_SHORT]
    )

    for week in month_days:
        row: list[InlineKeyboardButton] = []
        for day_num in week:
            if day_num == 0:
                row.append(InlineKeyboardButton(" ", callback_data="cal:ignore"))
                continue

            day = date(year, month, day_num)
            if not _date_in_range(day, today, max_date):
                row.append(InlineKeyboardButton("·", callback_data="cal:ignore"))
                continue

            label = str(day_num)
            row.append(
                InlineKeyboardButton(
                    label,
                    callback_data=f"cal:day:{day.isoformat()}",
                )
            )
        rows.append(row)

    prev_month = date(year, month, 1) - timedelta(days=1)
    next_month = date(year, month, 28) + timedelta(days=4)
    next_month = next_month.replace(day=1)

    nav_row: list[InlineKeyboardButton] = []
    if _date_in_range(prev_month.replace(day=15), today, max_date) or (
        prev_month.year == today.year and prev_month.month >= today.month
    ):
        nav_row.append(
            InlineKeyboardButton(
                "◀",
                callback_data=f"cal:nav:{prev_month.year}:{prev_month.month}",
            )
        )
    else:
        nav_row.append(InlineKeyboardButton(" ", callback_data="cal:ignore"))

    nav_row.append(InlineKeyboardButton("✕", callback_data="book:cancel"))

    if next_month <= max_date.replace(day=1) or (
        next_month.year < max_date.year
        or (next_month.year == max_date.year and next_month.month <= max_date.month)
    ):
        nav_row.append(
            InlineKeyboardButton(
                "▶",
                callback_data=f"cal:nav:{next_month.year}:{next_month.month}",
            )
        )
    else:
        nav_row.append(InlineKeyboardButton(" ", callback_data="cal:ignore"))

    rows.append(nav_row)
    return InlineKeyboardMarkup(rows)


def time_slots_keyboard(booking_date: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []

    start = datetime.strptime(f"{booking_date} {WORK_START_HOUR:02d}:00", "%Y-%m-%d %H:%M")
    end = datetime.strptime(f"{booking_date} {WORK_END_HOUR:02d}:00", "%Y-%m-%d %H:%M")
    now = datetime.now()

    current = start
    while current < end:
        time_label = current.strftime("%H:%M")
        if booking_date == date.today().isoformat() and current <= now:
            current += timedelta(minutes=SLOT_MINUTES)
            continue

        if is_slot_taken(booking_date, time_label):
            current += timedelta(minutes=SLOT_MINUTES)
            continue

        row.append(
            InlineKeyboardButton(
                time_label,
                callback_data=f"time:{booking_date}:{time_label}",
            )
        )
        if len(row) == 3:
            rows.append(row)
            row = []
        current += timedelta(minutes=SLOT_MINUTES)

    if row:
        rows.append(row)

    if not rows:
        rows.append(
            [InlineKeyboardButton("Нет свободных слотов", callback_data="cal:ignore")]
        )

    rows.append([InlineKeyboardButton("◀ Назад", callback_data="book:start")])
    return InlineKeyboardMarkup(rows)


def haircut_keyboard() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for key, item in HAIRCUT_STYLES.items():
        rows.append(
            [
                InlineKeyboardButton(
                    f"{item['emoji']} {item['name']} — {item['price']} ₽",
                    callback_data=f"hair:{key}",
                )
            ]
        )
    rows.append([InlineKeyboardButton("◀ Назад", callback_data="book:back_time")])
    return InlineKeyboardMarkup(rows)


def beard_keyboard() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for key, item in BEARD_STYLES.items():
        price = "0 ₽" if item["price"] == 0 else f"{item['price']} ₽"
        rows.append(
            [
                InlineKeyboardButton(
                    f"{item['emoji']} {item['name']} — {price}",
                    callback_data=f"beard:{key}",
                )
            ]
        )
    rows.append([InlineKeyboardButton("◀ Назад", callback_data="book:back_hair")])
    return InlineKeyboardMarkup(rows)


def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("◈ Подтвердить", callback_data="book:confirm"),
                InlineKeyboardButton("✕ Отмена", callback_data="book:cancel"),
            ]
        ]
    )


def format_date_label(iso_date: str) -> str:
    d = date.fromisoformat(iso_date)
    return f"{WEEKDAY_SHORT[d.weekday()]}, {d.day} {MONTH_NAMES[d.month - 1]}"
