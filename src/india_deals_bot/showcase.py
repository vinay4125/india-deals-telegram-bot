from __future__ import annotations

import sys
from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

from .config import Settings, load_env_file
from .telegram import TelegramClient

WEBSITE_URL = "https://vinay4125.github.io/india-deals-telegram-bot/deals.html"
PHOTO_URL = "https://vinay4125.github.io/india-deals-telegram-bot/showcase-card.png"


def build_caption(now: datetime | None = None) -> str:
    current = now or datetime.now(ZoneInfo("Asia/Kolkata"))
    greeting = "Good morning" if current.hour < 12 else "Good evening"
    return (
        f"✨ <b>{escape(greeting)} from India Best Deals!</b>\n\n"
        "🔥 Browse selected shopping promotions and official retailer offers.\n"
        "⚡ Genuine ₹1 and flash deals are highlighted when available.\n"
        "📍 Quick-commerce prices can vary by pincode, account and stock.\n\n"
        "Tap below to see the current showcase.\n\n"
        "<i>Some website links may be affiliate links. We may earn from "
        "qualifying purchases at no additional cost to you.</i>"
    )


def main() -> int:
    try:
        load_env_file()
        settings = Settings.from_env()
        TelegramClient(
            settings.telegram_bot_token, settings.telegram_chat_id
        ).send_showcase(
            photo_url=PHOTO_URL,
            caption=build_caption(),
            website_url=WEBSITE_URL,
        )
    except (RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print("Posted public showcase")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
