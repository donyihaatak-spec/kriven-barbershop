import json
from typing import Any

from datetime import date

from catalog import BEARD_STYLES, HAIRCUT_STYLES
from config import PREPAY_MIN, PREPAY_NAME, PREPAY_PERCENT, PREPAY_PHONE
from database import (
    STATUS_CANCELLED,
    STATUS_CONFIRMED,
    STATUS_PENDING,
    cancel_booking,
    confirm_booking,
    create_booking,
    get_admin_bookings,
    get_admin_stats,
    get_booked_times_for_date,
    get_booking_by_id,
    get_user_bookings,
)
from keyboards import format_date_label

import branding


def calc_prepayment(total: int) -> int:
    if total <= 0:
        return 0
    amount = max(PREPAY_MIN, round(total * PREPAY_PERCENT / 100))
    return min(amount, total)


def booking_payload_from_row(row: dict) -> dict[str, Any]:
    haircut = HAIRCUT_STYLES.get(row["haircut_key"], {"name": row["haircut_key"]})
    beard = BEARD_STYLES.get(row["beard_key"], {"name": row["beard_key"]})
    total = row["total_price"]
    prepay = row.get("prepayment_amount") or calc_prepayment(total)
    return {
        "booking_id": row["id"],
        "user_id": row["user_id"],
        "date_label": format_date_label(row["booking_date"]),
        "time": row["booking_time"],
        "haircut": haircut["name"],
        "beard": beard["name"],
        "total": total,
        "prepayment": prepay,
        "rest": max(total - prepay, 0),
        "payment_code": row.get("payment_code") or "",
        "status": row.get("status", STATUS_PENDING),
    }


def get_slots_api_data(iso_date: str) -> dict[str, Any]:
    booked = get_booked_times_for_date(iso_date)
    return {"date": iso_date, "booked": booked}


def get_my_bookings_api(user_id: int) -> list[dict[str, Any]]:
    rows = get_user_bookings(user_id)
    result = []
    for row in rows:
        payload = booking_payload_from_row(row)
        result.append(
            {
                "date": row["booking_date"],
                "date_label": payload["date_label"],
                "time": payload["time"],
                "haircut": payload["haircut"],
                "beard": payload["beard"],
                "total": payload["total"],
                "prepayment": payload["prepayment"],
                "rest": payload["rest"],
                "payment_code": payload["payment_code"],
                "status": payload["status"],
            }
        )
    return result


def submit_booking(
    user_id: int,
    username: str | None,
    full_name: str | None,
    booking_date: str,
    booking_time: str,
    haircut_key: str,
    beard_key: str,
) -> tuple[bool, str, dict[str, Any] | None]:
    if haircut_key not in HAIRCUT_STYLES or beard_key not in BEARD_STYLES:
        return False, "Неверные услуги", None

    haircut = HAIRCUT_STYLES[haircut_key]
    beard = BEARD_STYLES[beard_key]
    total = haircut["price"] + beard["price"]
    prepay = calc_prepayment(total)

    booking_id = create_booking(
        user_id=user_id,
        username=username,
        full_name=full_name,
        booking_date=booking_date,
        booking_time=booking_time,
        haircut_key=haircut_key,
        beard_key=beard_key,
        total_price=total,
        prepayment_amount=prepay,
        status=STATUS_PENDING,
    )

    if not booking_id:
        return False, branding.slot_taken(), None

    row = get_booking_by_id(booking_id)
    if not row:
        return False, "Ошибка создания записи", None

    payload = booking_payload_from_row(row)
    message = branding.booking_pending(
        payload["date_label"],
        booking_time,
        haircut["name"],
        beard["name"],
        total,
        prepay,
        total - prepay,
        payload["payment_code"],
        PREPAY_PHONE,
        PREPAY_NAME,
    )
    return True, message, payload


def admin_confirm_booking(booking_id: int) -> tuple[bool, str, dict[str, Any] | None]:
    row = confirm_booking(booking_id)
    if not row:
        return False, "Запись не найдена или уже обработана", None
    return True, "confirmed", booking_payload_from_row(row)


def admin_cancel_booking(booking_id: int) -> tuple[bool, str, dict[str, Any] | None]:
    row = cancel_booking(booking_id)
    if not row:
        return False, "Запись не найдена или уже обработана", None
    return True, "cancelled", booking_payload_from_row(row)


def user_confirmed_message(payload: dict[str, Any]) -> str:
    return branding.booking_success(
        payload["date_label"],
        payload["time"],
        payload["haircut"],
        payload["beard"],
        payload["total"],
        payload["prepayment"],
        payload["rest"],
    )


def user_cancelled_message(payload: dict[str, Any]) -> str:
    return branding.booking_payment_rejected(
        payload["date_label"],
        payload["time"],
    )


def format_admin_booking(row: dict) -> dict[str, Any]:
    payload = booking_payload_from_row(row)
    payload["username"] = row.get("username")
    payload["full_name"] = row.get("full_name") or "—"
    payload["created_at"] = row.get("created_at", "")
    return payload


def get_admin_dashboard_api(filter_name: str = "pending") -> dict[str, Any]:
    stats = get_admin_stats()
    today = date.today().isoformat()

    if filter_name == "pending":
        rows = get_admin_bookings(status=STATUS_PENDING)
    elif filter_name == "today":
        rows = get_admin_bookings(booking_date=today)
    elif filter_name == "upcoming":
        rows = [
            row for row in get_admin_bookings(status=STATUS_CONFIRMED)
            if row["booking_date"] >= today
        ]
    else:
        rows = get_admin_bookings(status="all")

    return {
        "stats": stats,
        "bookings": [format_admin_booking(row) for row in rows],
    }


def admin_notification_text(
    full_name: str,
    username: str | None,
    payload: dict[str, Any],
    source: str = "Mini App",
) -> str:
    prepay = payload.get("prepayment", 0)
    rest = payload.get("rest", payload["total"] - prepay)
    code = payload.get("payment_code", "—")
    return (
        f"⏳ Ожидает оплату ({source})\n\n"
        f"👤 {full_name} (@{username or '—'})\n"
        f"📅 {payload['date_label']}, {payload['time']}\n"
        f"✂️ {payload['haircut']}\n"
        f"🧔 {payload['beard']}\n"
        f"💰 Итого: {branding.price_tag(payload['total'])}\n"
        f"✅ Предоплата: {branding.price_tag(prepay)}\n"
        f"💵 В барбершопе: {branding.price_tag(rest)}\n\n"
        f"🔑 Код в комментарии: {code}\n\n"
        "Проверь перевод в банке и нажми кнопку ниже."
    )


def catalog_for_webapp() -> str:
    return json.dumps(
        {
            "haircuts": HAIRCUT_STYLES,
            "beards": BEARD_STYLES,
            "config": {
                "workStart": 10,
                "workEnd": 20,
                "slotMinutes": 30,
                "closedWeekdays": [6],
                "daysAhead": 30,
                "prepayPercent": PREPAY_PERCENT,
                "prepayMin": PREPAY_MIN,
                "prepayPhone": PREPAY_PHONE,
                "prepayName": PREPAY_NAME,
            },
        },
        ensure_ascii=False,
    )
