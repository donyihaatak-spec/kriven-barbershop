import json
import logging
from pathlib import Path

from aiohttp import web

from admin_auth import admin_auth_enabled, check_admin_password, create_admin_token, verify_admin_token
from admin_service import (
    create_gallery_item_api,
    create_review_api,
    get_admin_barbers_api,
    get_admin_clients_api,
    get_admin_gallery_api,
    get_admin_logs_api,
    get_admin_overview_api,
    get_admin_reviews_api,
    get_admin_services_api,
    get_admin_settings_api,
    get_admin_users_api,
)
from booking_service import (
    admin_cancel_booking,
    admin_confirm_booking,
    get_admin_dashboard_api,
    user_cancelled_message,
    user_confirmed_message,
)
from database import delete_gallery_item, delete_review
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


async def _read_json(request: web.Request) -> dict:
    try:
        return await request.json()
    except json.JSONDecodeError:
        return {}


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
    body = await _read_json(request)
    password = body.get("password", "")
    if not check_admin_password(password):
        return web.json_response({"ok": False, "error": "Неверный пароль"}, status=403)
    return web.json_response({"ok": True, "token": create_admin_token()})


async def handle_admin_dashboard(request: web.Request) -> web.Response:
    _require_admin(request)
    filter_name = request.query.get("filter", "pending")
    data = get_admin_dashboard_api(filter_name)
    return web.json_response({"ok": True, **data})


async def handle_admin_overview(request: web.Request) -> web.Response:
    _require_admin(request)
    return web.json_response({"ok": True, **get_admin_overview_api()})


async def handle_admin_clients(request: web.Request) -> web.Response:
    _require_admin(request)
    return web.json_response({"ok": True, "clients": get_admin_clients_api()})


async def handle_admin_services(request: web.Request) -> web.Response:
    _require_admin(request)
    return web.json_response({"ok": True, **get_admin_services_api()})


async def handle_admin_barbers(request: web.Request) -> web.Response:
    _require_admin(request)
    return web.json_response({"ok": True, "barbers": get_admin_barbers_api()})


async def handle_admin_reviews(request: web.Request) -> web.Response:
    _require_admin(request)
    return web.json_response({"ok": True, "reviews": get_admin_reviews_api()})


async def handle_admin_review_create(request: web.Request) -> web.Response:
    _require_admin(request)
    body = await _read_json(request)
    review_id = create_review_api(
        body.get("author", ""),
        body.get("text", ""),
        int(body.get("rating", 5)),
    )
    if not review_id:
        return web.json_response({"ok": False, "error": "Заполни имя и текст"}, status=400)
    return web.json_response({"ok": True, "id": review_id})


async def handle_admin_review_delete(request: web.Request) -> web.Response:
    _require_admin(request)
    review_id = int(request.match_info["review_id"])
    if not delete_review(review_id):
        return web.json_response({"ok": False, "error": "Не найдено"}, status=404)
    return web.json_response({"ok": True})


async def handle_admin_gallery(request: web.Request) -> web.Response:
    _require_admin(request)
    return web.json_response({"ok": True, "items": get_admin_gallery_api()})


async def handle_admin_gallery_create(request: web.Request) -> web.Response:
    _require_admin(request)
    body = await _read_json(request)
    item_id = create_gallery_item_api(body.get("title", ""), body.get("image_url", ""))
    if not item_id:
        return web.json_response({"ok": False, "error": "Заполни название и ссылку"}, status=400)
    return web.json_response({"ok": True, "id": item_id})


async def handle_admin_gallery_delete(request: web.Request) -> web.Response:
    _require_admin(request)
    item_id = int(request.match_info["item_id"])
    if not delete_gallery_item(item_id):
        return web.json_response({"ok": False, "error": "Не найдено"}, status=404)
    return web.json_response({"ok": True})


async def handle_admin_settings(request: web.Request) -> web.Response:
    _require_admin(request)
    return web.json_response({"ok": True, "settings": get_admin_settings_api()})


async def handle_admin_users(request: web.Request) -> web.Response:
    _require_admin(request)
    return web.json_response({"ok": True, "users": get_admin_users_api()})


async def handle_admin_logs(request: web.Request) -> web.Response:
    _require_admin(request)
    return web.json_response({"ok": True, "logs": get_admin_logs_api()})


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
    app.router.add_get("/api/admin/overview", handle_admin_overview)
    app.router.add_get("/api/admin/clients", handle_admin_clients)
    app.router.add_get("/api/admin/services", handle_admin_services)
    app.router.add_get("/api/admin/barbers", handle_admin_barbers)
    app.router.add_get("/api/admin/reviews", handle_admin_reviews)
    app.router.add_post("/api/admin/reviews", handle_admin_review_create)
    app.router.add_delete("/api/admin/reviews/{review_id}", handle_admin_review_delete)
    app.router.add_get("/api/admin/gallery", handle_admin_gallery)
    app.router.add_post("/api/admin/gallery", handle_admin_gallery_create)
    app.router.add_delete("/api/admin/gallery/{item_id}", handle_admin_gallery_delete)
    app.router.add_get("/api/admin/settings", handle_admin_settings)
    app.router.add_get("/api/admin/users", handle_admin_users)
    app.router.add_get("/api/admin/logs", handle_admin_logs)
    app.router.add_post("/api/admin/bookings/{booking_id}/confirm", handle_admin_confirm)
    app.router.add_post("/api/admin/bookings/{booking_id}/cancel", handle_admin_cancel)
    app.router.add_static("/admin/assets", ADMIN_DIR, show_index=False)
