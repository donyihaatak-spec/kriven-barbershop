import asyncio
import logging
from datetime import date, datetime, timedelta

from branding import booking_reminder
from booking_service import booking_payload_from_row
from settings_store import get_reminder_enabled, get_reminder_hour
from database import get_bookings_for_reminder, mark_reminder_sent
from telegram_notify import send_telegram_message

logger = logging.getLogger(__name__)


async def process_reminders() -> None:
    if not get_reminder_enabled():
        return

    now = datetime.now()
    if now.hour < get_reminder_hour():
        return

    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    rows = get_bookings_for_reminder(tomorrow)
    if not rows:
        return

    for row in rows:
        payload = booking_payload_from_row(row)
        text = booking_reminder(
            payload["date_label"],
            payload["time"],
            payload["haircut"],
            payload["beard"],
        )
        sent = await send_telegram_message(row["user_id"], text)
        if sent:
            mark_reminder_sent(row["id"])
            logger.info("Reminder sent for booking %s", row["id"])


async def reminder_loop() -> None:
    logger.info("Reminder loop started (hour >= %s)", REMINDER_HOUR)
    while True:
        try:
            await process_reminders()
        except Exception:
            logger.exception("Reminder check failed")
        await asyncio.sleep(900)
