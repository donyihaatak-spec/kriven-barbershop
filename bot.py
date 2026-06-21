import asyncio
import logging
import sys

from telegram import MenuButtonWebApp, WebAppInfo
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters
from telegram.request import HTTPXRequest

from bot_runtime import abort_if_render_webhook_active
from config import BOT_TOKEN, WEBAPP_URL
from database import init_db
from handlers import admin_command, booking_callback, menu_callback, payment_callback, price_command, start_command
from webapp_handlers import webapp_data_handler

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    await abort_if_render_webhook_active(application.bot)
    if WEBAPP_URL:
        await application.bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="◈ Записаться",
                web_app=WebAppInfo(url=WEBAPP_URL),
            )
        )


def main() -> None:
    if not BOT_TOKEN or BOT_TOKEN == "your_telegram_bot_token_here":
        print("Ошибка: укажи BOT_TOKEN в файле .env")
        print("1. Открой @BotFather в Telegram")
        print("2. Создай бота командой /newbot")
        print("3. Скопируй токен в .env")
        sys.exit(1)

    init_db()

    request = HTTPXRequest(httpx_kwargs={"trust_env": False})
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .request(request)
        .get_updates_request(request)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("price", price_command))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, webapp_data_handler))
    app.add_handler(CallbackQueryHandler(menu_callback, pattern=r"^menu:"))
    app.add_handler(CallbackQueryHandler(payment_callback, pattern=r"^pay:"))
    app.add_handler(CallbackQueryHandler(booking_callback))

    logger.info("KRIVEN Barbershop bot started")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
