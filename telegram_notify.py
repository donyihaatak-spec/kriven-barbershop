import logging

import aiohttp

from config import BOT_TOKEN

logger = logging.getLogger(__name__)


async def send_telegram_message(chat_id: int | str, text: str) -> bool:
    if not BOT_TOKEN:
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        async with aiohttp.ClientSession(trust_env=False) as session:
            async with session.post(
                url,
                json={"chat_id": str(chat_id), "text": text},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.error("Telegram API error %s: %s", resp.status, body)
                    return False
                return True
    except Exception:
        logger.exception("Failed to send Telegram message")
        return False
