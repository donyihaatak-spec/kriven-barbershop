"""Настройки салона и барберы в SQLite — редактируются из админки."""
from __future__ import annotations

import json
import re
import unicodedata

from config import (
    ADMIN_CHAT_ID as ENV_ADMIN_CHAT_ID,
    ADMIN_PASSWORD as ENV_ADMIN_PASSWORD,
    BARBERS as DEFAULT_BARBERS,
    BOOKING_DAYS_AHEAD as ENV_BOOKING_DAYS_AHEAD,
    CLOSED_WEEKDAYS as ENV_CLOSED_WEEKDAYS,
    PREPAY_MIN as ENV_PREPAY_MIN,
    PREPAY_NAME as ENV_PREPAY_NAME,
    PREPAY_PERCENT as ENV_PREPAY_PERCENT,
    PREPAY_PHONE as ENV_PREPAY_PHONE,
    REMINDER_ENABLED as ENV_REMINDER_ENABLED,
    REMINDER_HOUR as ENV_REMINDER_HOUR,
    SLOT_MINUTES as ENV_SLOT_MINUTES,
    WORK_END_HOUR as ENV_WORK_END_HOUR,
    WORK_START_HOUR as ENV_WORK_START_HOUR,
)
from database import DB_PATH
import sqlite3

_cache: dict[str, str] | None = None
_barbers_cache: list[dict] | None = None


def _slugify(name: str) -> str:
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return text or "barber"


def invalidate_settings_cache() -> None:
    global _cache, _barbers_cache
    _cache = None
    _barbers_cache = None


def init_settings_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS shop_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS barbers (
            barber_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT '',
            active INTEGER NOT NULL DEFAULT 1,
            sort_order INTEGER NOT NULL DEFAULT 0
        )
        """
    )


def seed_settings_defaults(conn: sqlite3.Connection) -> None:
    defaults = {
        "shop_name": "KRIVEN BARBERS",
        "prepay_percent": str(ENV_PREPAY_PERCENT),
        "prepay_min": str(ENV_PREPAY_MIN),
        "prepay_phone": ENV_PREPAY_PHONE,
        "prepay_name": ENV_PREPAY_NAME,
        "work_start_hour": str(ENV_WORK_START_HOUR),
        "work_end_hour": str(ENV_WORK_END_HOUR),
        "slot_minutes": str(ENV_SLOT_MINUTES),
        "closed_weekdays": json.dumps(sorted(ENV_CLOSED_WEEKDAYS)),
        "booking_days_ahead": str(ENV_BOOKING_DAYS_AHEAD),
        "reminder_enabled": "1" if ENV_REMINDER_ENABLED else "0",
        "reminder_hour": str(ENV_REMINDER_HOUR),
        "admin_chat_id": ENV_ADMIN_CHAT_ID or "",
        "admin_password": "",
    }
    for key, value in defaults.items():
        conn.execute(
            "INSERT OR IGNORE INTO shop_settings (key, value) VALUES (?, ?)",
            (key, value),
        )

    count = conn.execute("SELECT COUNT(*) FROM barbers").fetchone()[0]
    if count:
        return
    for order, barber in enumerate(DEFAULT_BARBERS):
        conn.execute(
            """
            INSERT INTO barbers (barber_id, name, role, active, sort_order)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                barber["id"],
                barber["name"],
                barber.get("role", ""),
                int(barber.get("active", True)),
                order,
            ),
        )


def _load_cache() -> dict[str, str]:
    global _cache
    if _cache is not None:
        return _cache
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("SELECT key, value FROM shop_settings").fetchall()
    _cache = {row[0]: row[1] for row in rows}
    return _cache


def _get_raw(key: str, fallback: str = "") -> str:
    return _load_cache().get(key, fallback)


def _get_int(key: str, fallback: int) -> int:
    try:
        return int(_get_raw(key, str(fallback)))
    except (TypeError, ValueError):
        return fallback


def _get_bool(key: str, fallback: bool) -> bool:
    raw = _get_raw(key, "1" if fallback else "0").lower()
    return raw in ("1", "true", "yes")


def get_shop_name() -> str:
    return _get_raw("shop_name", "KRIVEN BARBERS")


def get_prepay_percent() -> int:
    return _get_int("prepay_percent", ENV_PREPAY_PERCENT)


def get_prepay_min() -> int:
    return _get_int("prepay_min", ENV_PREPAY_MIN)


def get_prepay_phone() -> str:
    return _get_raw("prepay_phone", ENV_PREPAY_PHONE)


def get_prepay_name() -> str:
    return _get_raw("prepay_name", ENV_PREPAY_NAME)


def get_work_start_hour() -> int:
    return _get_int("work_start_hour", ENV_WORK_START_HOUR)


def get_work_end_hour() -> int:
    return _get_int("work_end_hour", ENV_WORK_END_HOUR)


def get_slot_minutes() -> int:
    return _get_int("slot_minutes", ENV_SLOT_MINUTES)


def get_closed_weekdays() -> set[int]:
    raw = _get_raw("closed_weekdays", json.dumps(sorted(ENV_CLOSED_WEEKDAYS)))
    try:
        values = json.loads(raw)
        return {int(v) for v in values}
    except (TypeError, ValueError, json.JSONDecodeError):
        return set(ENV_CLOSED_WEEKDAYS)


def get_booking_days_ahead() -> int:
    return _get_int("booking_days_ahead", ENV_BOOKING_DAYS_AHEAD)


def get_reminder_enabled() -> bool:
    return _get_bool("reminder_enabled", ENV_REMINDER_ENABLED)


def get_reminder_hour() -> int:
    return _get_int("reminder_hour", ENV_REMINDER_HOUR)


def get_admin_chat_id() -> str:
    return _get_raw("admin_chat_id", ENV_ADMIN_CHAT_ID or "")


def get_admin_password() -> str:
    db_password = _get_raw("admin_password", "")
    if db_password:
        return db_password
    return ENV_ADMIN_PASSWORD


def get_all_settings_admin() -> dict:
    closed = sorted(get_closed_weekdays())
    return {
        "shop_name": get_shop_name(),
        "prepay_percent": get_prepay_percent(),
        "prepay_min": get_prepay_min(),
        "prepay_phone": get_prepay_phone(),
        "prepay_name": get_prepay_name(),
        "work_start_hour": get_work_start_hour(),
        "work_end_hour": get_work_end_hour(),
        "slot_minutes": get_slot_minutes(),
        "closed_weekdays": closed,
        "booking_days_ahead": get_booking_days_ahead(),
        "reminder_enabled": get_reminder_enabled(),
        "reminder_hour": get_reminder_hour(),
        "admin_chat_id": get_admin_chat_id(),
        "password_from_db": bool(_get_raw("admin_password", "")),
    }


def save_settings_admin(data: dict) -> bool:
    updates: dict[str, str] = {}

    if "shop_name" in data:
        name = str(data["shop_name"]).strip()
        if not name:
            return False
        updates["shop_name"] = name

    for key in ("prepay_percent", "prepay_min", "work_start_hour", "work_end_hour", "slot_minutes", "booking_days_ahead", "reminder_hour"):
        if key in data:
            updates[key] = str(max(0, int(data[key])))

    if "prepay_phone" in data:
        updates["prepay_phone"] = str(data["prepay_phone"]).strip()
    if "prepay_name" in data:
        updates["prepay_name"] = str(data["prepay_name"]).strip()
    if "admin_chat_id" in data:
        updates["admin_chat_id"] = str(data["admin_chat_id"]).strip()
    if "reminder_enabled" in data:
        updates["reminder_enabled"] = "1" if data["reminder_enabled"] else "0"
    if "closed_weekdays" in data:
        days = sorted({int(d) for d in data["closed_weekdays"] if 0 <= int(d) <= 6})
        updates["closed_weekdays"] = json.dumps(days)

    if not updates:
        return False

    with sqlite3.connect(DB_PATH) as conn:
        for key, value in updates.items():
            conn.execute(
                """
                INSERT INTO shop_settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )
    invalidate_settings_cache()
    return True


def change_admin_password(current: str, new_password: str) -> tuple[bool, str]:
    if not new_password or len(new_password) < 4:
        return False, "Пароль минимум 4 символа"
    if not current or current != get_admin_password():
        return False, "Неверный текущий пароль"
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO shop_settings (key, value) VALUES ('admin_password', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (new_password,),
        )
    invalidate_settings_cache()
    return True, ""


def get_barbers(active_only: bool = False) -> list[dict]:
    global _barbers_cache
    if active_only and _barbers_cache is not None:
        return [b for b in _barbers_cache if b.get("active")]

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        query = "SELECT barber_id, name, role, active, sort_order FROM barbers"
        if active_only:
            query += " WHERE active = 1"
        query += " ORDER BY sort_order, barber_id"
        rows = conn.execute(query).fetchall()

    barbers = [
        {
            "id": row["barber_id"],
            "name": row["name"],
            "role": row["role"],
            "active": bool(row["active"]),
            "sort_order": row["sort_order"],
        }
        for row in rows
    ]
    if not active_only:
        _barbers_cache = barbers
    return barbers


def get_all_barbers_admin() -> list[dict]:
    return get_barbers(active_only=False)


def upsert_barber(barber_id: str, name: str, role: str = "", active: bool = True) -> bool:
    barber_id = barber_id.strip().lower().replace(" ", "_")
    name = name.strip()
    if not barber_id or not name:
        return False
    with sqlite3.connect(DB_PATH) as conn:
        exists = conn.execute(
            "SELECT 1 FROM barbers WHERE barber_id = ?",
            (barber_id,),
        ).fetchone()
        if exists:
            conn.execute(
                "UPDATE barbers SET name = ?, role = ?, active = ? WHERE barber_id = ?",
                (name, role.strip(), int(active), barber_id),
            )
        else:
            max_order = conn.execute("SELECT COALESCE(MAX(sort_order), -1) FROM barbers").fetchone()[0]
            conn.execute(
                """
                INSERT INTO barbers (barber_id, name, role, active, sort_order)
                VALUES (?, ?, ?, ?, ?)
                """,
                (barber_id, name, role.strip(), int(active), max_order + 1),
            )
    invalidate_settings_cache()
    _barbers_cache = None
    return True


def create_barber(name: str, role: str = "", barber_id: str | None = None) -> str | None:
    key = (barber_id or _slugify(name)).strip().lower().replace(" ", "_")
    if upsert_barber(key, name, role, True):
        return key
    return None


def set_barber_active(barber_id: str, active: bool) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "UPDATE barbers SET active = ? WHERE barber_id = ?",
            (int(active), barber_id),
        )
        ok = conn.total_changes > 0
    if ok:
        invalidate_settings_cache()
        global _barbers_cache
        _barbers_cache = None
    return ok
