import asyncio
import logging
import os

from aiohttp import web
from telegram import MenuButtonWebApp, Update, WebAppInfo
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters
from telegram.request import HTTPXRequest

from config import ADMIN_CHAT_ID, BOT_TOKEN, WEBAPP_URL
from database import init_db
from handlers import admin_command, booking_callback, menu_callback, payment_callback, price_command, start_command
from server import create_app
from reminders import reminder_loop
from webapp_handlers import webapp_data_handler

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

ptb_app: Application | None = None


def get_public_url() -> str:
    return (WEBAPP_URL or os.getenv("RENDER_EXTERNAL_URL", "")).rstrip("/")


def build_ptb_app() -> Application:
    request = HTTPXRequest(httpx_kwargs={"trust_env": False})
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .request(request)
        .updater(None)
        .build()
    )
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("price", price_command))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, webapp_data_handler))
    app.add_handler(CallbackQueryHandler(menu_callback, pattern=r"^menu:"))
    app.add_handler(CallbackQueryHandler(payment_callback, pattern=r"^pay:"))
    app.add_handler(CallbackQueryHandler(booking_callback))
    return app


async def webhook_handler(request: web.Request) -> web.Response:
    if not ptb_app:
        return web.Response(status=503, text="bot not ready")
    try:
        data = await request.json()
        update = Update.de_json(data, ptb_app.bot)
        await ptb_app.process_update(update)
    except Exception:
        logger.exception("Webhook update failed")
        return web.Response(status=500, text="error")
    return web.Response(text="ok")


async def health_handler(_request: web.Request) -> web.Response:
    return web.Response(text="ok")


async def on_startup(web_app: web.Application) -> None:
    global ptb_app

    init_db()
    ptb_app = build_ptb_app()
    await ptb_app.initialize()
    await ptb_app.start()

    public_url = get_public_url()
    if not public_url:
        logger.warning("WEBAPP_URL / RENDER_EXTERNAL_URL не задан")
        return

    import config

    config.WEBAPP_URL = public_url

    webhook_url = f"{public_url}/webhook"
    await ptb_app.bot.set_webhook(
        url=webhook_url,
        allowed_updates=["message", "callback_query"],
    )
    await ptb_app.bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(
            text="Записаться",
            web_app=WebAppInfo(url=public_url),
        )
    )
    logger.info("Webhook: %s", webhook_url)
    logger.info("Mini App: %s", public_url)
    asyncio.create_task(reminder_loop())


async def on_cleanup(_web_app: web.Application) -> None:
    if ptb_app:
        await ptb_app.stop()
        await ptb_app.shutdown()


def main() -> None:
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN не задан")

    web_app = create_app()
    web_app.router.add_post("/webhook", webhook_handler)
    web_app.router.add_get("/health", health_handler)
    web_app.on_startup.append(on_startup)
    web_app.on_cleanup.append(on_cleanup)

    port = int(os.getenv("PORT", "8080"))
    logger.info("Запуск на порту %s", port)
    web.run_app(web_app, host="0.0.0.0", port=port, print=None)


if __name__ == "__main__":
    main()
