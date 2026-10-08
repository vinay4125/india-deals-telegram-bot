from __future__ import annotations

from html import escape

from .http import request_json
from .models import Deal


def format_deal(deal: Deal) -> str:
    return (
        f"🔥 <b>{escape(deal.title)}</b>\n\n"
        f"🏪 {escape(deal.merchant)}\n"
        f"💰 <b>₹{deal.sale_price:,.0f}</b> "
        f"<s>₹{deal.list_price:,.0f}</s>\n"
        f"🏷️ <b>{deal.discount_percent}% OFF</b>\n\n"
        f'<a href="{escape(deal.url, quote=True)}">View deal</a>\n'
        "⚠️ Price and availability can change."
    )


class TelegramClient:
    def __init__(self, bot_token: str, chat_id: str) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id

    def send_deal(self, deal: Deal) -> None:
        payload = request_json(
            f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
            method="POST",
            data={
                "chat_id": self.chat_id,
                "text": format_deal(deal),
                "parse_mode": "HTML",
                "disable_web_page_preview": False,
            },
            error_label="Telegram Bot API",
        )
        if not payload.get("ok"):
            raise RuntimeError(f"Telegram rejected the message: {payload}")
