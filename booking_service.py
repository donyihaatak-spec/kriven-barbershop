import json
from typing import Any

from catalog import BEARD_STYLES, HAIRCUT_STYLES
from config import PREPAY_MIN, PREPAY_NAME, PREPAY_PERCENT, PREPAY_PHONE
from database import create_booking, get_booked_times_for_date, get_user_bookings
from keyboards import format_date_label

import branding


def calc_prepayment(total: int) -> int:
    if total <= 0:
        return 0
    amount = max(PREPAY_MIN, round(total * PREPAY_PERCENT / 100))
    return min(amount, total)


def get_slots_api_data(iso_date: str) -> dict[str, Any]:
    booked = get_booked_times_for_date(iso_date)
    return {"date": iso_date, "booked": booked}


def get_my_bookings_api(user_id: int) -> list[dict[str, Any]]:
    rows = get_user_bookings(user_id)
    result = []
    for row in rows:
        haircut = HAIRCUT_STYLES.get(row["haircut_key"], {"name": row["haircut_key"]})
        beard = BEARD_STYLES.get(row["beard_key"], {"name": row["beard_key"]})
        total = row["total_price"]
        prepay = row.get("prepayment_amount") or calc_prepayment(total)
        result.append(
            {
                "date": row["booking_date"],
                "date_label": format_date_label(row["booking_date"]),
                "time": row["booking_time"],
                "haircut": haircut["name"],
                "beard": beard["name"],
                "total": total,
                "prepayment": prepay,
                "rest": max(total - prepay, 0),
                "prepayment_confirmed": bool(row.get("prepayment_confirmed")),
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
    prepayment_confirmed: bool = False,
) -> tuple[bool, str, dict[str, Any] | None]:
    if haircut_key not in HAIRCUT_STYLES or beard_key not in BEARD_STYLES:
        return False, "Неверные услуги", None

    if not prepayment_confirmed:
        return False, "Подтверди, что перевёл предоплату", None

    haircut = HAIRCUT_STYLES[haircut_key]
    beard = BEARD_STYLES[beard_key]
    total = haircut["price"] + beard["price"]
    prepay = calc_prepayment(total)

    ok = create_booking(
        user_id=user_id,
        username=username,
        full_name=full_name,
        booking_date=booking_date,
        booking_time=booking_time,
        haircut_key=haircut_key,
        beard_key=beard_key,
        total_price=total,
        prepayment_amount=prepay,
        prepayment_confirmed=True,
    )

    if not ok:
        return False, branding.slot_taken(), None

    payload = {
        "date_label": format_date_label(booking_date),
        "time": booking_time,
        "haircut": haircut["name"],
        "beard": beard["name"],
        "total": total,
        "prepayment": prepay,
        "rest": total - prepay,
    }
    success = branding.booking_success(
        payload["date_label"],
        booking_time,
        haircut["name"],
        beard["name"],
        total,
        prepay,
        total - prepay,
    )
    return True, success, payload


def admin_notification_text(
    full_name: str,
    username: str | None,
    payload: dict[str, Any],
    source: str = "Mini App",
) -> str:
    prepay = payload.get("prepayment", 0)
    rest = payload.get("rest", payload["total"] - prepay)
    return (
        f"📋 Новая запись ({source})\n"
        f"👤 {full_name} (@{username or '—'})\n"
        f"📅 {payload['date_label']}, {payload['time']}\n"
        f"✂️ {payload['haircut']}\n"
        f"🧔 {payload['beard']}\n"
        f"💰 Итого: {branding.price_tag(payload['total'])}\n"
        f"✅ Предоплата: {branding.price_tag(prepay)}\n"
        f"💵 В барбершопе: {branding.price_tag(rest)}"
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
