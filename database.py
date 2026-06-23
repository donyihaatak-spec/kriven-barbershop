import secrets
import sqlite3
from datetime import date, datetime

from config import DB_PATH

STATUS_PENDING = "pending"
STATUS_CONFIRMED = "confirmed"
STATUS_CANCELLED = "cancelled"


def _migrate(conn: sqlite3.Connection) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(bookings)")}
    if "prepayment_amount" not in cols:
        conn.execute("ALTER TABLE bookings ADD COLUMN prepayment_amount INTEGER NOT NULL DEFAULT 0")
    if "prepayment_confirmed" not in cols:
        conn.execute("ALTER TABLE bookings ADD COLUMN prepayment_confirmed INTEGER NOT NULL DEFAULT 0")
    if "status" not in cols:
        conn.execute("ALTER TABLE bookings ADD COLUMN status TEXT NOT NULL DEFAULT 'confirmed'")
        conn.execute(
            "UPDATE bookings SET status = ? WHERE prepayment_confirmed = 0",
            (STATUS_PENDING,),
        )
    if "payment_code" not in cols:
        conn.execute("ALTER TABLE bookings ADD COLUMN payment_code TEXT")
    if "reminder_sent" not in cols:
        conn.execute("ALTER TABLE bookings ADD COLUMN reminder_sent INTEGER NOT NULL DEFAULT 0")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author TEXT NOT NULL,
            text TEXT NOT NULL,
            rating INTEGER NOT NULL DEFAULT 5,
            created_at TEXT NOT NULL,
            published INTEGER NOT NULL DEFAULT 1
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS gallery_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            image_url TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                full_name TEXT,
                booking_date TEXT NOT NULL,
                booking_time TEXT NOT NULL,
                haircut_key TEXT NOT NULL,
                beard_key TEXT NOT NULL,
                total_price INTEGER NOT NULL,
                prepayment_amount INTEGER NOT NULL DEFAULT 0,
                prepayment_confirmed INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'pending',
                payment_code TEXT,
                created_at TEXT NOT NULL,
                UNIQUE(booking_date, booking_time)
            )
            """
        )
        _migrate(conn)
        from catalog_store import init_catalog_table, seed_catalog_defaults
        from settings_store import init_settings_tables, seed_settings_defaults

        init_catalog_table(conn)
        seed_catalog_defaults(conn)
        from catalog_store import ensure_placeholder_services

        ensure_placeholder_services(conn)
        init_settings_tables(conn)
        seed_settings_defaults(conn)
        _seed_gallery(conn)


def _seed_gallery(conn: sqlite3.Connection) -> None:
    count = conn.execute("SELECT COUNT(*) FROM gallery_items").fetchone()[0]
    if count:
        return
    now = datetime.now().isoformat()
    conn.execute(
        """
        INSERT INTO gallery_items (title, image_url, created_at)
        VALUES (?, ?, ?), (?, ?, ?)
        """,
        (
            "KRIVEN BARBERS",
            "/admin/assets/icon.png",
            now,
            "Интерьер",
            "/admin/assets/icon.png",
            now,
        ),
    )


def generate_payment_code() -> str:
    return f"KRV-{secrets.token_hex(2).upper()}"


def get_booked_times_for_date(booking_date: str) -> list[str]:
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT booking_time FROM bookings
            WHERE booking_date = ? AND status != ?
            """,
            (booking_date, STATUS_CANCELLED),
        ).fetchall()
    return [row[0] for row in rows]


def is_slot_taken(booking_date: str, booking_time: str) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            """
            SELECT 1 FROM bookings
            WHERE booking_date = ? AND booking_time = ? AND status != ?
            """,
            (booking_date, booking_time, STATUS_CANCELLED),
        ).fetchone()
    return row is not None


def create_booking(
    user_id: int,
    username: str | None,
    full_name: str | None,
    booking_date: str,
    booking_time: str,
    haircut_key: str,
    beard_key: str,
    total_price: int,
    prepayment_amount: int = 0,
    payment_code: str | None = None,
    status: str = STATUS_PENDING,
) -> int | None:
    code = payment_code or generate_payment_code()
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.execute(
                """
                INSERT INTO bookings (
                    user_id, username, full_name, booking_date, booking_time,
                    haircut_key, beard_key, total_price,
                    prepayment_amount, prepayment_confirmed, status, payment_code, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
                """,
                (
                    user_id,
                    username,
                    full_name,
                    booking_date,
                    booking_time,
                    haircut_key,
                    beard_key,
                    total_price,
                    prepayment_amount,
                    status,
                    code,
                    datetime.now().isoformat(),
                ),
            )
            return int(cur.lastrowid)
    except sqlite3.IntegrityError:
        return None


def get_booking_by_id(booking_id: int) -> dict | None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
    return dict(row) if row else None


def confirm_booking(booking_id: int) -> dict | None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute(
            """
            UPDATE bookings
            SET status = ?, prepayment_confirmed = 1
            WHERE id = ? AND status = ?
            """,
            (STATUS_CONFIRMED, booking_id, STATUS_PENDING),
        )
        if conn.total_changes == 0:
            return None
        row = conn.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
    return dict(row) if row else None


def cancel_booking(booking_id: int) -> dict | None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute(
            """
            UPDATE bookings
            SET status = ?
            WHERE id = ? AND status = ?
            """,
            (STATUS_CANCELLED, booking_id, STATUS_PENDING),
        )
        if conn.total_changes == 0:
            return None
        row = conn.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
    return dict(row) if row else None


def _booking_is_in_future(row: dict) -> bool:
    try:
        hour, minute = map(int, str(row["booking_time"]).split(":")[:2])
        booking_day = date.fromisoformat(row["booking_date"])
        booking_dt = datetime(booking_day.year, booking_day.month, booking_day.day, hour, minute)
        return booking_dt > datetime.now()
    except (TypeError, ValueError):
        return False


def user_cancel_booking(booking_id: int, user_id: int) -> dict | None:
    row = get_booking_by_id(booking_id)
    if not row or row["user_id"] != user_id:
        return None
    if row["status"] not in (STATUS_PENDING, STATUS_CONFIRMED):
        return None
    if not _booking_is_in_future(row):
        return None

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute(
            """
            UPDATE bookings
            SET status = ?
            WHERE id = ? AND user_id = ? AND status IN (?, ?)
            """,
            (STATUS_CANCELLED, booking_id, user_id, STATUS_PENDING, STATUS_CONFIRMED),
        )
        if conn.total_changes == 0:
            return None
        updated = conn.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
    return dict(updated) if updated else None


def can_user_cancel(row: dict) -> bool:
    return row.get("status") in (STATUS_PENDING, STATUS_CONFIRMED) and _booking_is_in_future(row)


def get_bookings_for_reminder(reminder_date: str) -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT * FROM bookings
            WHERE booking_date = ?
              AND status = ?
              AND reminder_sent = 0
            """,
            (reminder_date, STATUS_CONFIRMED),
        ).fetchall()
    return [dict(row) for row in rows]


def mark_reminder_sent(booking_id: int) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "UPDATE bookings SET reminder_sent = 1 WHERE id = ?",
            (booking_id,),
        )


def get_user_booking_by_code(user_id: int, payment_code: str) -> dict | None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM bookings WHERE user_id = ? AND payment_code = ?",
            (user_id, payment_code),
        ).fetchone()
    return dict(row) if row else None


def get_user_bookings(user_id: int) -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT * FROM bookings
            WHERE user_id = ? AND booking_date >= ? AND status != ?
            ORDER BY booking_date, booking_time
            """,
            (user_id, date.today().isoformat(), STATUS_CANCELLED),
        ).fetchall()
    return [dict(row) for row in rows]


def get_admin_bookings(status: str | None = None, booking_date: str | None = None) -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        query = "SELECT * FROM bookings WHERE 1=1"
        params: list = []

        if status and status != "all":
            query += " AND status = ?"
            params.append(status)
        elif status != "all":
            query += " AND status != ?"
            params.append(STATUS_CANCELLED)

        if booking_date:
            query += " AND booking_date = ?"
            params.append(booking_date)

        query += " ORDER BY booking_date DESC, booking_time DESC LIMIT 200"
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def get_admin_stats() -> dict:
    today = date.today().isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        pending = conn.execute(
            "SELECT COUNT(*) FROM bookings WHERE status = ?",
            (STATUS_PENDING,),
        ).fetchone()[0]
        today_total = conn.execute(
            """
            SELECT COUNT(*) FROM bookings
            WHERE booking_date = ? AND status != ?
            """,
            (today, STATUS_CANCELLED),
        ).fetchone()[0]
        today_confirmed = conn.execute(
            """
            SELECT COUNT(*) FROM bookings
            WHERE booking_date = ? AND status = ?
            """,
            (today, STATUS_CONFIRMED),
        ).fetchone()[0]
        upcoming = conn.execute(
            """
            SELECT COUNT(*) FROM bookings
            WHERE booking_date >= ? AND status = ?
            """,
            (today, STATUS_CONFIRMED),
        ).fetchone()[0]
    return {
        "pending": pending,
        "today_total": today_total,
        "today_confirmed": today_confirmed,
        "upcoming_confirmed": upcoming,
    }


def get_admin_clients() -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT
                user_id,
                MAX(full_name) AS full_name,
                MAX(username) AS username,
                COUNT(*) AS bookings_count,
                SUM(CASE WHEN status = 'confirmed' THEN 1 ELSE 0 END) AS confirmed_count,
                MAX(created_at) AS last_booking
            FROM bookings
            WHERE status != ?
            GROUP BY user_id
            ORDER BY last_booking DESC
            LIMIT 200
            """,
            (STATUS_CANCELLED,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_admin_logs(limit: int = 50) -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, full_name, username, status, created_at,
                   booking_date, booking_time, payment_code, total_price
            FROM bookings
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_reviews() -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM reviews ORDER BY created_at DESC LIMIT 100"
        ).fetchall()
    return [dict(row) for row in rows]


def add_review(author: str, text: str, rating: int) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            """
            INSERT INTO reviews (author, text, rating, created_at, published)
            VALUES (?, ?, ?, ?, 1)
            """,
            (author, text, rating, datetime.now().isoformat()),
        )
        return int(cur.lastrowid)


def delete_review(review_id: int) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM reviews WHERE id = ?", (review_id,))
        return conn.total_changes > 0


def update_review(review_id: int, author: str, text: str, rating: int) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "UPDATE reviews SET author = ?, text = ?, rating = ? WHERE id = ?",
            (author, text, rating, review_id),
        )
        return conn.total_changes > 0


def get_gallery_items() -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM gallery_items ORDER BY created_at DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def add_gallery_item(title: str, image_url: str) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            """
            INSERT INTO gallery_items (title, image_url, created_at)
            VALUES (?, ?, ?)
            """,
            (title, image_url, datetime.now().isoformat()),
        )
        return int(cur.lastrowid)


def delete_gallery_item(item_id: int) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM gallery_items WHERE id = ?", (item_id,))
        return conn.total_changes > 0


def update_gallery_item(item_id: int, title: str, image_url: str) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "UPDATE gallery_items SET title = ?, image_url = ? WHERE id = ?",
            (title, image_url, item_id),
        )
        return conn.total_changes > 0
