import asyncio
import logging
import sys
import threading

from telegram import Bot, MenuButtonWebApp, WebAppInfo
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters
from telegram.request import HTTPXRequest

from bot_runtime import abort_if_render_webhook_active
from config import BOT_TOKEN, WEBAPP_PORT, WEBAPP_URL
from database import init_db
from handlers import booking_callback, menu_callback, price_command, start_command
from server import run_server
from tunnel_manager import TUNNEL_URL, start_tunnel
from webapp_handlers import webapp_data_handler

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main() -> None:
    if not BOT_TOKEN or BOT_TOKEN == "your_telegram_bot_token_here":
        print("Ошибка: укажи BOT_TOKEN в файле .env")
        sys.exit(1)

    init_db()

    server_thread = threading.Thread(
        target=run_server,
        args=(WEBAPP_PORT,),
        daemon=True,
    )
    server_thread.start()
    logger.info("Сервер Mini App: http://127.0.0.1:%s", WEBAPP_PORT)

    webapp_url = start_tunnel(WEBAPP_PORT) or WEBAPP_URL
    if not webapp_url:
        print("\n[!] Туннель не поднялся. Проверь интернет и SSH.\n")
        sys.exit(1)

    import config
    config.WEBAPP_URL = webapp_url

    print(f"\n[OK] Mini App: {webapp_url}\n")

    async def post_init(application: Application) -> None:
        await abort_if_render_webhook_active(application.bot)
        await application.bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="Записаться",
                web_app=WebAppInfo(url=webapp_url),
            )
        )
        logger.info("Кнопка Mini App: %s", webapp_url)

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
    app.add_handler(CommandHandler("price", price_command))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, webapp_data_handler))
    app.add_handler(CallbackQueryHandler(menu_callback, pattern=r"^menu:"))
    app.add_handler(CallbackQueryHandler(booking_callback))

    logger.info("KRIVEN bot запущен")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
