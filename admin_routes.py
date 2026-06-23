import json
import logging
from pathlib import Path

from aiohttp import web

from admin_auth import admin_auth_enabled, check_admin_password, create_admin_token, verify_admin_token
from booking_service import (
    admin_cancel_booking,
    admin_confirm_booking,
    get_admin_dashboard_api,
    user_cancelled_message,
    user_confirmed_message,
)
from telegram_notify import send_telegram_message

logger = logging.getLogger(__name__)
ADMIN_DIR = Path(__file__).parent / "admin-panel"


def _no_cache(response: web.FileResponse) -> web.FileResponse:
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


def _extract_token(request: web.Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:].strip()
    return request.headers.get("X-Admin-Token", "").strip() or None


def _require_admin(request: web.Request) -> None:
    if not verify_admin_token(_extract_token(request)):
        raise web.HTTPUnauthorized(
            text=json.dumps({"ok": False, "error": "Нужен вход"}, ensure_ascii=False),
            content_type="application/json",
        )


async def handle_admin_index(_request: web.Request) -> web.FileResponse:
    return _no_cache(web.FileResponse(ADMIN_DIR / "index.html"))


async def handle_admin_demo(_request: web.Request) -> web.FileResponse:
    return _no_cache(web.FileResponse(ADMIN_DIR / "demo.html"))


async def handle_admin_login(request: web.Request) -> web.Response:
    if not admin_auth_enabled():
        return web.json_response(
            {"ok": False, "error": "Задай ADMIN_PASSWORD в Render"},
            status=503,
        )
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"ok": False, "error": "Неверный формат"}, status=400)

    password = body.get("password", "")
    if not check_admin_password(password):
        return web.json_response({"ok": False, "error": "Неверный пароль"}, status=403)

    return web.json_response({"ok": True, "token": create_admin_token()})


async def handle_admin_dashboard(request: web.Request) -> web.Response:
    _require_admin(request)
    filter_name = request.query.get("filter", "pending")
    data = get_admin_dashboard_api(filter_name)
    return web.json_response({"ok": True, **data})


async def handle_admin_confirm(request: web.Request) -> web.Response:
    _require_admin(request)
    booking_id = int(request.match_info["booking_id"])
    ok, _, payload = admin_confirm_booking(booking_id)
    if not ok or not payload:
        return web.json_response({"ok": False, "error": "Уже обработано или не найдено"}, status=400)

    await send_telegram_message(payload["user_id"], user_confirmed_message(payload))
    return web.json_response({"ok": True, "booking": payload})


async def handle_admin_cancel(request: web.Request) -> web.Response:
    _require_admin(request)
    booking_id = int(request.match_info["booking_id"])
    ok, _, payload = admin_cancel_booking(booking_id)
    if not ok or not payload:
        return web.json_response({"ok": False, "error": "Уже обработано или не найдено"}, status=400)

    await send_telegram_message(payload["user_id"], user_cancelled_message(payload))
    return web.json_response({"ok": True, "booking": payload})


def register_admin_routes(app: web.Application) -> None:
    app.router.add_get("/admin", handle_admin_index)
    app.router.add_get("/admin/demo", handle_admin_demo)
    app.router.add_post("/api/admin/login", handle_admin_login)
    app.router.add_get("/api/admin/dashboard", handle_admin_dashboard)
    app.router.add_post("/api/admin/bookings/{booking_id}/confirm", handle_admin_confirm)
    app.router.add_post("/api/admin/bookings/{booking_id}/cancel", handle_admin_cancel)
    app.router.add_static(
        "/admin/assets",
        ADMIN_DIR,
        show_index=False,
        cache_max_age=0,
    )
