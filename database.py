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
