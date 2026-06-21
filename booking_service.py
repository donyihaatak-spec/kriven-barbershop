import json
from typing import Any

from catalog import BEARD_STYLES, HAIRCUT_STYLES
from database import create_booking, get_booked_times_for_date
from keyboards import format_date_label

import branding


def get_slots_api_data(iso_date: str) -> dict[str, Any]:
    booked = get_booked_times_for_date(iso_date)
    return {"date": iso_date, "booked": booked}


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

    ok = create_booking(
        user_id=user_id,
        username=username,
        full_name=full_name,
        booking_date=booking_date,
        booking_time=booking_time,
        haircut_key=haircut_key,
        beard_key=beard_key,
        total_price=total,
    )

    if not ok:
        return False, branding.slot_taken(), None

    payload = {
        "date_label": format_date_label(booking_date),
        "time": booking_time,
        "haircut": haircut["name"],
        "beard": beard["name"],
        "total": total,
    }
    success = branding.booking_success(
        payload["date_label"],
        booking_time,
        haircut["name"],
        beard["name"],
        total,
    )
    return True, success, payload


def admin_notification_text(
    full_name: str,
    username: str | None,
    payload: dict[str, Any],
    source: str = "Mini App",
) -> str:
    return (
        f"📋 Новая запись ({source})\n"
        f"👤 {full_name} (@{username or '—'})\n"
        f"📅 {payload['date_label']}, {payload['time']}\n"
        f"✂️ {payload['haircut']}\n"
        f"🧔 {payload['beard']}\n"
        f"💰 {branding.price_tag(payload['total'])}"
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
            },
        },
        ensure_ascii=False,
    )
