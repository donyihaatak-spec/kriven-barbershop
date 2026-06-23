"""Данные для разделов админ-панели."""
from __future__ import annotations

from datetime import date

import branding
from catalog import BEARD_STYLES, HAIRCUT_STYLES
from config import (
    ADMIN_CHAT_ID,
    BARBERS,
    BOOKING_DAYS_AHEAD,
    CLOSED_WEEKDAYS,
    PREPAY_MIN,
    PREPAY_NAME,
    PREPAY_PERCENT,
    PREPAY_PHONE,
    REMINDER_ENABLED,
    REMINDER_HOUR,
    SLOT_MINUTES,
    WORK_END_HOUR,
    WORK_START_HOUR,
)
from database import (
    add_gallery_item,
    add_review,
    delete_gallery_item,
    delete_review,
    get_admin_bookings,
    get_admin_clients,
    get_admin_logs,
    get_admin_stats,
    get_gallery_items,
    get_reviews,
)
from booking_service import format_admin_booking, get_admin_dashboard_api
from keyboards import format_date_label

WEEKDAY_NAMES = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def get_admin_overview_api() -> dict:
    dashboard = get_admin_dashboard_api("all")
    recent = [format_admin_booking(row) for row in get_admin_bookings(status="all")[:8]]
    return {
        "stats": dashboard["stats"],
        "recent": recent,
    }


def get_admin_clients_api() -> list[dict]:
    clients = []
    for row in get_admin_clients():
        clients.append(
            {
                "user_id": row["user_id"],
                "full_name": row.get("full_name") or "—",
                "username": row.get("username"),
                "bookings_count": row["bookings_count"],
                "confirmed_count": row["confirmed_count"],
                "last_booking": row.get("last_booking", ""),
            }
        )
    return clients


def get_admin_services_api() -> dict:
    haircuts = [
        {"key": key, "name": item["name"], "price": item["price"], "emoji": item.get("emoji", "")}
        for key, item in HAIRCUT_STYLES.items()
    ]
    beards = [
        {"key": key, "name": item["name"], "price": item["price"], "emoji": item.get("emoji", "")}
        for key, item in BEARD_STYLES.items()
    ]
    return {"haircuts": haircuts, "beards": beards}


def get_admin_barbers_api() -> list[dict]:
    return BARBERS


def get_admin_reviews_api() -> list[dict]:
    return [
        {
            "id": row["id"],
            "author": row["author"],
            "text": row["text"],
            "rating": row["rating"],
            "created_at": row["created_at"],
        }
        for row in get_reviews()
    ]


def get_admin_gallery_api() -> list[dict]:
    return [
        {
            "id": row["id"],
            "title": row["title"],
            "image_url": row["image_url"],
            "created_at": row["created_at"],
        }
        for row in get_gallery_items()
    ]


def get_admin_settings_api() -> dict:
    closed = ", ".join(WEEKDAY_NAMES[d] for d in sorted(CLOSED_WEEKDAYS))
    return {
        "shop_name": branding.SHOP_NAME,
        "prepay_percent": PREPAY_PERCENT,
        "prepay_min": PREPAY_MIN,
        "prepay_phone": PREPAY_PHONE,
        "prepay_name": PREPAY_NAME,
        "work_hours": f"{WORK_START_HOUR}:00 – {WORK_END_HOUR}:00",
        "slot_minutes": SLOT_MINUTES,
        "closed_days": closed or "нет",
        "days_ahead": BOOKING_DAYS_AHEAD,
        "reminder_enabled": REMINDER_ENABLED,
        "reminder_hour": REMINDER_HOUR,
        "admin_chat_id": ADMIN_CHAT_ID or "не задан",
    }


def get_admin_users_api() -> list[dict]:
    return [
        {
            "id": "kriven_admin",
            "name": "kriven_admin",
            "role": "Владелец",
            "telegram_id": ADMIN_CHAT_ID or "—",
        }
    ]


def get_admin_logs_api() -> list[dict]:
    logs = []
    for row in get_admin_logs():
        status = row.get("status", "pending")
        if status == "confirmed":
            action = "Запись подтверждена"
        elif status == "cancelled":
            action = "Запись отменена"
        else:
            action = "Новая запись"
        logs.append(
            {
                "id": row["id"],
                "action": action,
                "full_name": row.get("full_name") or "—",
                "username": row.get("username"),
                "status": status,
                "datetime": f"{format_date_label(row['booking_date'])}, {row['booking_time']}",
                "payment_code": row.get("payment_code") or "",
                "total": row.get("total_price", 0),
                "created_at": row.get("created_at", ""),
            }
        )
    return logs


def create_review_api(author: str, text: str, rating: int = 5) -> int | None:
    author = author.strip()
    text = text.strip()
    if not author or not text:
        return None
    try:
        rating = int(rating)
    except (TypeError, ValueError):
        rating = 5
    rating = max(1, min(5, rating))
    return add_review(author, text, rating)


def create_gallery_item_api(title: str, image_url: str) -> int | None:
    title = title.strip()
    image_url = image_url.strip()
    if not title or not image_url:
        return None
    return add_gallery_item(title, image_url)
