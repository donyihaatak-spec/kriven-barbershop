"""HTTP-сервер для Telegram Mini App (статика + API)."""
import json
import logging
from pathlib import Path

from aiohttp import web

from admin_routes import register_admin_routes
from booking_service import (
    admin_notification_text,
    catalog_for_webapp,
    check_booking_status_api,
    get_my_bookings_api,
    get_slots_api_data,
    submit_booking,
)
from config import ADMIN_CHAT_ID, BOT_TOKEN
from keyboards import admin_payment_keyboard_api
from telegram_auth import validate_webapp_init_data
from telegram_notify import send_telegram_message

logger = logging.getLogger(__name__)
MINI_APP_DIR = Path(__file__).parent / "mini-app"


async def handle_catalog(_request: web.Request) -> web.Response:
    return web.Response(
        text=catalog_for_webapp(),
        content_type="application/json",
        charset="utf-8",
    )


async def handle_slots(request: web.Request) -> web.Response:
    iso_date = request.match_info["date"]
    data = get_slots_api_data(iso_date)
    return web.json_response(data)


async def handle_book(request: web.Request) -> web.Response:
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"ok": False, "error": "Неверный формат данных"}, status=400)

    init_data = body.get("initData", "")
    user = validate_webapp_init_data(init_data, BOT_TOKEN)
    if not user:
        return web.json_response(
            {"ok": False, "error": "Открой Mini App через кнопку в боте"},
            status=403,
        )

    required = ("date", "time", "haircut", "beard")
    if not all(body.get(k) for k in required):
        return web.json_response({"ok": False, "error": "Заполни все поля"}, status=400)

    ok, text, payload = submit_booking(
        user_id=int(user["id"]),
        username=user.get("username"),
        full_name=f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or None,
        booking_date=body["date"],
        booking_time=body["time"],
        haircut_key=body["haircut"],
        beard_key=body["beard"],
    )

    if ok and payload:
        await send_telegram_message(user["id"], text)
        if ADMIN_CHAT_ID:
            admin_text = admin_notification_text(
                f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or "—",
                user.get("username"),
                payload,
                source="Mini App",
            )
            await send_telegram_message(
                ADMIN_CHAT_ID,
                admin_text,
                reply_markup=admin_payment_keyboard_api(payload["booking_id"]),
            )

    return web.json_response({
        "ok": ok,
        "message": text,
        "pending": ok,
        "payment_code": payload.get("payment_code") if payload else None,
        "booking_id": payload.get("booking_id") if payload else None,
    })


async def handle_my_bookings(request: web.Request) -> web.Response:
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"ok": False, "error": "Неверный формат"}, status=400)

    init_data = body.get("initData", "")
    user = validate_webapp_init_data(init_data, BOT_TOKEN)
    if not user:
        return web.json_response({"ok": False, "error": "Открой через бота"}, status=403)

    bookings = get_my_bookings_api(int(user["id"]))
    return web.json_response({"ok": True, "bookings": bookings})


async def handle_booking_status(request: web.Request) -> web.Response:
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"ok": False, "error": "Неверный формат"}, status=400)

    init_data = body.get("initData", "")
    user = validate_webapp_init_data(init_data, BOT_TOKEN)
    if not user:
        return web.json_response({"ok": False, "error": "Открой через бота"}, status=403)

    payment_code = (body.get("payment_code") or "").strip()
    booking_id_raw = body.get("booking_id")
    booking_id = None
    if booking_id_raw is not None:
        try:
            booking_id = int(booking_id_raw)
        except (TypeError, ValueError):
            return web.json_response({"ok": False, "error": "Неверный ID записи"}, status=400)

    if not payment_code and not booking_id:
        return web.json_response({"ok": False, "error": "Нет кода оплаты"}, status=400)

    result = check_booking_status_api(int(user["id"]), payment_code or None, booking_id)
    if not result:
        return web.json_response({"ok": False, "error": "Запись не найдена"}, status=404)

    return web.json_response({"ok": True, **result})


async def handle_index(_request: web.Request) -> web.Response:
    return web.FileResponse(MINI_APP_DIR / "index.html")


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/", handle_index)
    register_admin_routes(app)
    app.router.add_get("/api/catalog", handle_catalog)
    app.router.add_get("/api/slots/{date}", handle_slots)
    app.router.add_post("/api/book", handle_book)
    app.router.add_post("/api/my-bookings", handle_my_bookings)
    app.router.add_post("/api/booking-status", handle_booking_status)
    app.router.add_static("/", MINI_APP_DIR, show_index=False)
    return app


def run_server(port: int) -> None:
    logging.basicConfig(level=logging.INFO)
    app = create_app()
    logger.info("Mini App server: http://127.0.0.1:%s", port)
    web.run_app(app, host="0.0.0.0", port=port, print=None)
