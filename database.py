import sqlite3
from datetime import date, datetime

from config import DB_PATH


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
                created_at TEXT NOT NULL,
                UNIQUE(booking_date, booking_time)
            )
            """
        )


def get_booked_times_for_date(booking_date: str) -> list[str]:
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT booking_time FROM bookings WHERE booking_date = ?",
            (booking_date,),
        ).fetchall()
    return [row[0] for row in rows]


def is_slot_taken(booking_date: str, booking_time: str) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT 1 FROM bookings WHERE booking_date = ? AND booking_time = ?",
            (booking_date, booking_time),
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
) -> bool:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """
                INSERT INTO bookings (
                    user_id, username, full_name, booking_date, booking_time,
                    haircut_key, beard_key, total_price, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    datetime.now().isoformat(),
                ),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def get_user_bookings(user_id: int) -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT * FROM bookings
            WHERE user_id = ? AND booking_date >= ?
            ORDER BY booking_date, booking_time
            """,
            (user_id, date.today().isoformat()),
        ).fetchall()
    return [dict(row) for row in rows]
