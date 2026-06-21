"""Shared helpers for local bot runners."""

from __future__ import annotations

import sys

from telegram import Bot


async def abort_if_render_webhook_active(bot: Bot) -> None:
    info = await bot.get_webhook_info()
    url = (info.url or "").lower()
    if "onrender.com" in url:
        print()
        print("=" * 60)
        print("  Бот уже работает на Render — локально не запускай.")
        print(f"  Webhook: {info.url}")
        print()
        print("  Открой Telegram: @kriventestbot")
        print("  Напиши /start и подожди до 30 сек (сервер может просыпаться).")
        print()
        print("  start.bat / run.py ломают Render, если запускать одновременно.")
        print("=" * 60)
        print()
        sys.exit(0)
