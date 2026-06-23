import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")
WEBAPP_URL = os.getenv("WEBAPP_URL", "") or os.getenv("RENDER_EXTERNAL_URL", "")
WEBAPP_PORT = int(os.getenv("WEBAPP_PORT", "8080"))

PREPAY_PERCENT = int(os.getenv("PREPAY_PERCENT", "50"))
PREPAY_MIN = int(os.getenv("PREPAY_MIN", "300"))
PREPAY_PHONE = os.getenv("PREPAY_PHONE", "+79000000000")
PREPAY_NAME = os.getenv("PREPAY_NAME", "KRIVEN BARBERS")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

REMINDER_ENABLED = os.getenv("REMINDER_ENABLED", "true").lower() in ("1", "true", "yes")
REMINDER_HOUR = int(os.getenv("REMINDER_HOUR", "18"))

SALES_MODE = os.getenv("SALES_MODE", "").lower() in ("1", "true", "yes")
SALES_CONTACT_URL = os.getenv("SALES_CONTACT_URL", "https://t.me/bonnement")
KWORK_URL = os.getenv("KWORK_URL", "https://kwork.ru/user/bonnement")

DB_PATH = Path(os.getenv("DB_PATH", str(Path(__file__).parent / "bookings.db")))


def public_webapp_url() -> str:
    return WEBAPP_URL.rstrip("/") if WEBAPP_URL else ""

# Рабочие часы барбершопа
WORK_START_HOUR = 10
WORK_END_HOUR = 20
SLOT_MINUTES = 30

# Выходные: 0 = понедельник, 6 = воскресенье
CLOSED_WEEKDAYS: set[int] = {6}

# Сколько дней вперёд можно записаться
BOOKING_DAYS_AHEAD = 30

# Барберы салона (для админки)
BARBERS = [
    {
        "id": "kriven",
        "name": "KRIVEN",
        "role": "Топ-мастер",
        "active": True,
    },
]
