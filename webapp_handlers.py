import json
import logging

from telegram import Update
from telegram.ext import ContextTypes

from booking_service import admin_notification_text, submit_booking
from config import ADMIN_CHAT_ID
from keyboards import main_menu_keyboard

logger = logging.getLogger(__name__)


async def webapp_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message or not message.web_app_data:
        return

    user = update.effective_user
    if not user:
        return

    try:
        data = json.loads(message.web_app_data.data)
    except json.JSONDecodeError:
        await message.reply_text("Ошибка данных. Попробуй снова.")
        return

    required = ("date", "time", "haircut", "beard")
    if not all(data.get(k) for k in required):
        await message.reply_text("Не все поля заполнены. Запишись заново.")
        return

    ok, text, payload = submit_booking(
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
        booking_date=data["date"],
        booking_time=data["time"],
        haircut_key=data["haircut"],
        beard_key=data["beard"],
        prepayment_confirmed=bool(data.get("prepayment_confirmed")),
    )

    await message.reply_text(text, reply_markup=main_menu_keyboard())

    if ok and payload and ADMIN_CHAT_ID:
        admin_text = admin_notification_text(
            user.full_name or "—",
            user.username,
            payload,
            source="Mini App",
        )
        await context.bot.send_message(chat_id=int(ADMIN_CHAT_ID), text=admin_text)
