"""Прайс услуг в SQLite — редактируется из админки."""
from __future__ import annotations

import re
import unicodedata

from catalog import BEARD_STYLES as DEFAULT_BEARDS
from catalog import HAIRCUT_STYLES as DEFAULT_HAIRCUTS
from database import DB_PATH
import sqlite3

_cache: dict[str, dict[str, dict] | None] = {"haircut": None, "beard": None}


def _slugify(name: str) -> str:
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return text or "service"


def invalidate_catalog_cache() -> None:
    _cache["haircut"] = None
    _cache["beard"] = None


def init_catalog_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS catalog_services (
            kind TEXT NOT NULL,
            service_key TEXT NOT NULL,
            name TEXT NOT NULL,
            price INTEGER NOT NULL,
            emoji TEXT NOT NULL DEFAULT '',
            active INTEGER NOT NULL DEFAULT 1,
            sort_order INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (kind, service_key)
        )
        """
    )


def seed_catalog_defaults(conn: sqlite3.Connection) -> None:
    count = conn.execute("SELECT COUNT(*) FROM catalog_services").fetchone()[0]
    if count:
        return
    order = 0
    for key, item in DEFAULT_HAIRCUTS.items():
        conn.execute(
            """
            INSERT INTO catalog_services (kind, service_key, name, price, emoji, active, sort_order)
            VALUES ('haircut', ?, ?, ?, ?, 1, ?)
            """,
            (key, item["name"], item["price"], item.get("emoji", ""), order),
        )
        order += 1
    order = 0
    for key, item in DEFAULT_BEARDS.items():
        conn.execute(
            """
            INSERT INTO catalog_services (kind, service_key, name, price, emoji, active, sort_order)
            VALUES ('beard', ?, ?, ?, ?, 1, ?)
            """,
            (key, item["name"], item["price"], item.get("emoji", ""), order),
        )
        order += 1


def _rows_to_dict(rows: list) -> dict[str, dict]:
    result = {}
    for row in rows:
        result[row["service_key"]] = {
            "name": row["name"],
            "price": row["price"],
            "emoji": row["emoji"] or "",
            "active": bool(row["active"]),
        }
    return result


def get_services(kind: str, active_only: bool = True) -> dict[str, dict]:
    if kind not in ("haircut", "beard"):
        return {}
    if active_only and _cache.get(kind):
        return _cache[kind]  # type: ignore[return-value]

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        query = """
            SELECT service_key, name, price, emoji, active
            FROM catalog_services
            WHERE kind = ?
        """
        params: list = [kind]
        if active_only:
            query += " AND active = 1"
        query += " ORDER BY sort_order, service_key"
        rows = conn.execute(query, params).fetchall()

    data = _rows_to_dict(rows)
    if active_only:
        _cache[kind] = data
    return data


def get_haircut_styles() -> dict[str, dict]:
    return get_services("haircut", active_only=True)


def get_beard_styles() -> dict[str, dict]:
    return get_services("beard", active_only=True)


def get_all_services_admin(kind: str) -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT service_key, name, price, emoji, active, sort_order
            FROM catalog_services
            WHERE kind = ?
            ORDER BY sort_order, service_key
            """,
            (kind,),
        ).fetchall()
    return [
        {
            "key": row["service_key"],
            "name": row["name"],
            "price": row["price"],
            "emoji": row["emoji"] or "",
            "active": bool(row["active"]),
            "sort_order": row["sort_order"],
        }
        for row in rows
    ]


def upsert_service(
    kind: str,
    key: str,
    name: str,
    price: int,
    emoji: str = "",
    active: bool = True,
) -> bool:
    key = key.strip().lower().replace(" ", "_")
    name = name.strip()
    if not key or not name or kind not in ("haircut", "beard"):
        return False
    price = max(0, int(price))
    with sqlite3.connect(DB_PATH) as conn:
        exists = conn.execute(
            "SELECT 1 FROM catalog_services WHERE kind = ? AND service_key = ?",
            (kind, key),
        ).fetchone()
        if exists:
            conn.execute(
                """
                UPDATE catalog_services
                SET name = ?, price = ?, emoji = ?, active = ?
                WHERE kind = ? AND service_key = ?
                """,
                (name, price, emoji, int(active), kind, key),
            )
        else:
            max_order = conn.execute(
                "SELECT COALESCE(MAX(sort_order), -1) FROM catalog_services WHERE kind = ?",
                (kind,),
            ).fetchone()[0]
            conn.execute(
                """
                INSERT INTO catalog_services (kind, service_key, name, price, emoji, active, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (kind, key, name, price, emoji, int(active), max_order + 1),
            )
    invalidate_catalog_cache()
    return True


def create_service(kind: str, name: str, price: int, emoji: str = "", key: str | None = None) -> str | None:
    service_key = (key or _slugify(name)).strip().lower().replace(" ", "_")
    if not service_key:
        return None
    if upsert_service(kind, service_key, name, price, emoji, True):
        return service_key
    return None


def set_service_active(kind: str, key: str, active: bool) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "UPDATE catalog_services SET active = ? WHERE kind = ? AND service_key = ?",
            (int(active), kind, key),
        )
        ok = conn.total_changes > 0
    if ok:
        invalidate_catalog_cache()
    return ok
