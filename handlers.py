from datetime import date

from telegram import Update
from telegram.ext import ContextTypes

import branding
from booking_service import (
    admin_cancel_booking,
    admin_confirm_booking,
    admin_notification_text,
    booking_payload_from_row,
    calc_prepayment,
    user_cancelled_message,
    user_confirmed_message,
)
from catalog import BEARD_STYLES, HAIRCUT_STYLES
from config import ADMIN_CHAT_ID, PREPAY_NAME, PREPAY_PHONE, public_webapp_url
from database import create_booking, get_booking_by_id, get_user_bookings
from keyboards import (
    admin_payment_keyboard,
    beard_keyboard,
    calendar_keyboard,
    confirm_keyboard,
    format_date_label,
    haircut_keyboard,
    main_menu_keyboard,
    time_slots_keyboard,
)


def _get_session(context: ContextTypes.DEFAULT_TYPE) -> dict:
    return context.user_data.setdefault("booking", {})


def _is_admin(user_id: int) -> bool:
    return bool(ADMIN_CHAT_ID) and str(user_id) == str(ADMIN_CHAT_ID)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("booking", None)
    await update.message.reply_text(branding.welcome(), reply_markup=main_menu_keyboard())


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not _is_admin(user.id):
        await update.message.reply_text("Нет доступа.")
        return

    url = public_webapp_url()
    if not url:
        await update.message.reply_text("URL сервера не настроен.")
        return

    await update.message.reply_text(
        "◈ KRIVEN — админ-панель\n\n"
        f"Открой: {url}/admin?v=5\n\n"
        "Пароль — переменная ADMIN_PASSWORD в Render.\n"
        "Там все записи, подтверждение оплат и расписание."
    )


async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(branding.price_list(), reply_markup=main_menu_keyboard())


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == "menu:price":
        await query.edit_message_text(branding.price_list(), reply_markup=main_menu_keyboard())
        return

    if query.data == "menu:my":
        bookings = get_user_bookings(query.from_user.id)
        if not bookings:
            text = "У тебя пока нет активных записей."
        else:
            lines = ["Твои записи:", ""]
            for b in bookings:
                haircut = HAIRCUT_STYLES[b["haircut_key"]]["name"]
                beard = BEARD_STYLES[b["beard_key"]]["name"]
                status = b.get("status", "confirmed")
                status_label = "⏳ ждёт оплату" if status == "pending" else "✅ подтверждена"
                lines.append(
                    f"📅 {format_date_label(b['booking_date'])}, {b['booking_time']}\n"
                    f"✂️ {haircut} + 🧔 {beard}\n"
                    f"💰 {branding.price_tag(b['total_price'])}\n"
                    f"{status_label}\n"
                )
                if b.get("payment_code") and status == "pending":
                    lines.append(f"🔑 Код: {b['payment_code']}\n")
            text = "\n".join(lines)
        await query.edit_message_text(text, reply_markup=main_menu_keyboard())


async def payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not _is_admin(query.from_user.id):
        await query.answer("Только для админа", show_alert=True)
        return

    parts = (query.data or "").split(":")
    if len(parts) != 3:
        await query.answer()
        return

    action, booking_id_raw = parts[1], parts[2]
    try:
        booking_id = int(booking_id_raw)
    except ValueError:
        await query.answer("Неверный ID", show_alert=True)
        return

    if action == "confirm":
        ok, _, payload = admin_confirm_booking(booking_id)
        if not ok or not payload:
            await query.answer("Уже обработано или не найдено", show_alert=True)
            return

        await context.bot.send_message(
            chat_id=payload["user_id"],
            text=user_confirmed_message(payload),
            reply_markup=main_menu_keyboard(),
        )
        await query.edit_message_text(f"{query.message.text}\n\n✅ Подтверждено админом")
        await query.answer("Запись подтверждена")
        return

    if action == "cancel":
        ok, _, payload = admin_cancel_booking(booking_id)
        if not ok or not payload:
            await query.answer("Уже обработано или не найдено", show_alert=True)
            return

        await context.bot.send_message(
            chat_id=payload["user_id"],
            text=user_cancelled_message(payload),
            reply_markup=main_menu_keyboard(),
        )
        await query.edit_message_text(f"{query.message.text}\n\n❌ Отменено админом")
        await query.answer("Запись отменена")


async def booking_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data or ""
    session = _get_session(context)

    if data == "book:cancel":
        context.user_data.pop("booking", None)
        await query.edit_message_text(branding.booking_cancelled(), reply_markup=main_menu_keyboard())
        return

    if data == "book:start":
        today = date.today()
        await query.edit_message_text(
            branding.pick_date(),
            reply_markup=calendar_keyboard(today.year, today.month),
        )
        return

    if data.startswith("cal:nav:"):
        _, _, year, month = data.split(":")
        await query.edit_message_text(
            branding.pick_date(),
            reply_markup=calendar_keyboard(int(year), int(month)),
        )
        return

    if data.startswith("cal:day:"):
        iso_date = data.split(":", 2)[2]
        session["date"] = iso_date
        label = format_date_label(iso_date)
        await query.edit_message_text(
            branding.pick_time(label),
            reply_markup=time_slots_keyboard(iso_date),
        )
        return

    if data.startswith("time:"):
        _, iso_date, time_label = data.split(":", 2)
        session["date"] = iso_date
        session["time"] = time_label
        await query.edit_message_text(branding.pick_haircut(), reply_markup=haircut_keyboard())
        return

    if data == "book:back_time":
        iso_date = session.get("date")
        if not iso_date:
            today = date.today()
            await query.edit_message_text(
                branding.pick_date(),
                reply_markup=calendar_keyboard(today.year, today.month),
            )
            return
        label = format_date_label(iso_date)
        await query.edit_message_text(
            branding.pick_time(label),
            reply_markup=time_slots_keyboard(iso_date),
        )
        return

    if data.startswith("hair:"):
        session["haircut"] = data.split(":", 1)[1]
        await query.edit_message_text(branding.pick_beard(), reply_markup=beard_keyboard())
        return

    if data == "book:back_hair":
        await query.edit_message_text(branding.pick_haircut(), reply_markup=haircut_keyboard())
        return

    if data.startswith("beard:"):
        session["beard"] = data.split(":", 1)[1]
        haircut = HAIRCUT_STYLES[session["haircut"]]
        beard = BEARD_STYLES[session["beard"]]
        await query.edit_message_text(
            branding.confirmation(
                format_date_label(session["date"]),
                session["time"],
                haircut["name"],
                haircut["price"],
                beard["name"],
                beard["price"],
            ),
            reply_markup=confirm_keyboard(),
        )
        return

    if data == "book:confirm":
        required = ("date", "time", "haircut", "beard")
        if not all(session.get(k) for k in required):
            await query.edit_message_text(
                "Сессия истекла. Начни заново.",
                reply_markup=main_menu_keyboard(),
            )
            return

        haircut = HAIRCUT_STYLES[session["haircut"]]
        beard = BEARD_STYLES[session["beard"]]
        total = haircut["price"] + beard["price"]
        prepay = calc_prepayment(total)
        user = query.from_user

        booking_id = create_booking(
            user_id=user.id,
            username=user.username,
            full_name=user.full_name,
            booking_date=session["date"],
            booking_time=session["time"],
            haircut_key=session["haircut"],
            beard_key=session["beard"],
            total_price=total,
            prepayment_amount=prepay,
        )

        if not booking_id:
            await query.edit_message_text(
                branding.slot_taken(),
                reply_markup=time_slots_keyboard(session["date"]),
            )
            return

        row = get_booking_by_id(booking_id)
        code = row["payment_code"] if row else "—"

        pending_text = branding.booking_pending(
            format_date_label(session["date"]),
            session["time"],
            haircut["name"],
            beard["name"],
            total,
            prepay,
            total - prepay,
            code,
            PREPAY_PHONE,
            PREPAY_NAME,
        )
        await query.edit_message_text(pending_text, reply_markup=main_menu_keyboard())

        if ADMIN_CHAT_ID and row:
            payload = booking_payload_from_row(row)
            admin_text = admin_notification_text(
                user.full_name or "—",
                user.username,
                payload,
                source="Бот",
            )
            await context.bot.send_message(
                chat_id=int(ADMIN_CHAT_ID),
                text=admin_text,
                reply_markup=admin_payment_keyboard(booking_id),
            )

        context.user_data.pop("booking", None)
