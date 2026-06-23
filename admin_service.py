"""Данные для разделов админ-панели."""
from __future__ import annotations

from datetime import date

from catalog_store import (
    create_service,
    get_all_services_admin,
    set_service_active,
    upsert_service,
)
from settings_store import (
    change_admin_password,
    create_barber,
    get_admin_chat_id,
    get_all_barbers_admin,
    get_all_settings_admin,
    save_settings_admin,
    upsert_barber,
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
    update_gallery_item,
    update_review,
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
    haircuts = get_all_services_admin("haircut")
    beards = get_all_services_admin("beard")
    return {"haircuts": haircuts, "beards": beards}


def save_admin_service_api(
    kind: str,
    key: str,
    name: str,
    price: int,
    emoji: str = "",
    active: bool = True,
) -> bool:
    return upsert_service(kind, key, name, price, emoji, active)


def add_admin_service_api(
    kind: str,
    name: str,
    price: int,
    emoji: str = "",
    key: str | None = None,
) -> str | None:
    return create_service(kind, name, price, emoji, key)


def toggle_admin_service_api(kind: str, key: str, active: bool) -> bool:
    return set_service_active(kind, key, active)


def get_admin_barbers_api() -> list[dict]:
    return get_all_barbers_admin()


def save_admin_barber_api(barber_id: str, name: str, role: str, active: bool) -> bool:
    return upsert_barber(barber_id, name, role, active)


def add_admin_barber_api(name: str, role: str = "", barber_id: str | None = None) -> str | None:
    return create_barber(name, role, barber_id)


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
    settings = get_all_settings_admin()
    closed = ", ".join(WEEKDAY_NAMES[d] for d in settings["closed_weekdays"])
    settings["closed_days"] = closed or "нет"
    settings["work_hours"] = f"{settings['work_start_hour']}:00 – {settings['work_end_hour']}:00"
    return settings


def save_admin_settings_api(data: dict) -> bool:
    return save_settings_admin(data)


def change_admin_password_api(current: str, new_password: str) -> tuple[bool, str]:
    return change_admin_password(current, new_password)


def get_admin_users_api() -> list[dict]:
    chat_id = get_admin_chat_id()
    return [
        {
            "id": "kriven_admin",
            "name": "kriven_admin",
            "role": "Владелец",
            "telegram_id": chat_id or "—",
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


def update_review_api(review_id: int, author: str, text: str, rating: int = 5) -> bool:
    author = author.strip()
    text = text.strip()
    if not author or not text:
        return False
    try:
        rating = int(rating)
    except (TypeError, ValueError):
        rating = 5
    rating = max(1, min(5, rating))
    return update_review(review_id, author, text, rating)


def update_gallery_item_api(item_id: int, title: str, image_url: str) -> bool:
    title = title.strip()
    image_url = image_url.strip()
    if not title or not image_url:
        return False
    return update_gallery_item(item_id, title, image_url)
