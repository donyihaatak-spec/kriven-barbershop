import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")
WEBAPP_URL = os.getenv("WEBAPP_URL", "") or os.getenv("RENDER_EXTERNAL_URL", "")
WEBAPP_PORT = int(os.getenv("WEBAPP_PORT", "8080"))

DB_PATH = Path(os.getenv("DB_PATH", str(Path(__file__).parent / "bookings.db")))

# Рабочие часы барбершопа
WORK_START_HOUR = 10
WORK_END_HOUR = 20
SLOT_MINUTES = 30

# Выходные: 0 = понедельник, 6 = воскресенье
CLOSED_WEEKDAYS: set[int] = {6}

# Сколько дней вперёд можно записаться
BOOKING_DAYS_AHEAD = 30
