from datetime import date

from telegram import Update
from telegram.ext import ContextTypes

import branding
from catalog import BEARD_STYLES, HAIRCUT_STYLES
from config import ADMIN_CHAT_ID
from booking_service import calc_prepayment
from keyboards import (
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


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("booking", None)
    await update.message.reply_text(
        branding.welcome(),
        reply_markup=main_menu_keyboard(),
    )


async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        branding.price_list(),
        reply_markup=main_menu_keyboard(),
    )


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == "menu:price":
        await query.edit_message_text(
            branding.price_list(),
            reply_markup=main_menu_keyboard(),
        )
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
                lines.append(
                    f"📅 {format_date_label(b['booking_date'])}, {b['booking_time']}\n"
                    f"✂️ {haircut} + 🧔 {beard}\n"
                    f"💰 {branding.price_tag(b['total_price'])}\n"
                )
            text = "\n".join(lines)
        await query.edit_message_text(text, reply_markup=main_menu_keyboard())
        return


async def booking_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data or ""
    session = _get_session(context)

    if data == "book:cancel":
        context.user_data.pop("booking", None)
        await query.edit_message_text(
            branding.booking_cancelled(),
            reply_markup=main_menu_keyboard(),
        )
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
        await query.edit_message_text(
            branding.pick_haircut(),
            reply_markup=haircut_keyboard(),
        )
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
        await query.edit_message_text(
            branding.pick_beard(),
            reply_markup=beard_keyboard(),
        )
        return

    if data == "book:back_hair":
        await query.edit_message_text(
            branding.pick_haircut(),
            reply_markup=haircut_keyboard(),
        )
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

        ok = create_booking(
            user_id=user.id,
            username=user.username,
            full_name=user.full_name,
            booking_date=session["date"],
            booking_time=session["time"],
            haircut_key=session["haircut"],
            beard_key=session["beard"],
            total_price=total,
            prepayment_amount=prepay,
            prepayment_confirmed=False,
        )

        if not ok:
            label = format_date_label(session["date"])
            await query.edit_message_text(
                branding.slot_taken(),
                reply_markup=time_slots_keyboard(session["date"]),
            )
            return

        success_text = branding.booking_success(
            format_date_label(session["date"]),
            session["time"],
            haircut["name"],
            beard["name"],
            total,
            prepay,
            total - prepay,
        )
        await query.edit_message_text(success_text, reply_markup=main_menu_keyboard())

        if ADMIN_CHAT_ID:
            admin_text = (
                f"📋 Новая запись\n"
                f"👤 {user.full_name} (@{user.username or '—'})\n"
                f"📅 {format_date_label(session['date'])}, {session['time']}\n"
                f"✂️ {haircut['name']}\n"
                f"🧔 {beard['name']}\n"
                f"💰 {branding.price_tag(total)}"
            )
            await context.bot.send_message(chat_id=int(ADMIN_CHAT_ID), text=admin_text)

        context.user_data.pop("booking", None)
        return
