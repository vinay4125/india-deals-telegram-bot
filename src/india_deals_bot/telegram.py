from __future__ import annotations

from html import escape

from .http import request_json
from .models import Deal


def format_deal(deal: Deal) -> str:
    title = deal.title if len(deal.title) <= 500 else f"{deal.title[:497]}..."
    flash_label = "⚡ <b>₹1 / FLASH DEAL</b>\n" if deal.sale_price <= 10 else ""
    availability = (
        f"\n📍 {escape(deal.availability_note)}\n" if deal.availability_note else ""
    )
    return (
        f"{flash_label}🔥 <b>{escape(title)}</b>\n\n"
        f"🏪 {escape(deal.merchant)}\n"
        f"💰 <b>₹{deal.sale_price:,.0f}</b> "
        f"<s>₹{deal.list_price:,.0f}</s>\n"
        f"🏷️ <b>{deal.discount_percent}% OFF</b>\n"
        f"{availability}\n"
        f'<a href="{escape(deal.url, quote=True)}">View deal</a>\n'
        "⚠️ Price, stock and eligibility can vary by pincode and account."
    )


class TelegramClient:
    def __init__(self, bot_token: str, chat_id: str) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id

    def send_deal(self, deal: Deal) -> None:
        reply_markup = {
            "inline_keyboard": [[{"text": "🛍 View Deal", "url": deal.url}]]
        }
        if deal.image_url and deal.image_url.lower().startswith("https://"):
            payload = request_json(
                f"https://api.telegram.org/bot{self.bot_token}/sendPhoto",
                method="POST",
                data={
                    "chat_id": self.chat_id,
                    "photo": deal.image_url,
                    "caption": format_deal(deal),
                    "parse_mode": "HTML",
                    "reply_markup": reply_markup,
                },
                error_label="Telegram Bot API",
            )
        else:
            payload = request_json(
                f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                method="POST",
                data={
                    "chat_id": self.chat_id,
                    "text": format_deal(deal),
                    "parse_mode": "HTML",
                    "disable_web_page_preview": False,
                    "reply_markup": reply_markup,
                },
                error_label="Telegram Bot API",
            )
        if not payload.get("ok"):
            raise RuntimeError(f"Telegram rejected the deal message: {payload}")

    def send_showcase(self, *, photo_url: str, caption: str, website_url: str) -> None:
        payload = request_json(
            f"https://api.telegram.org/bot{self.bot_token}/sendPhoto",
            method="POST",
            data={
                "chat_id": self.chat_id,
                "photo": photo_url,
                "caption": caption,
                "parse_mode": "HTML",
                "reply_markup": {
                    "inline_keyboard": [
                        [{"text": "🔥 Browse Live Deals", "url": website_url}],
                        [
                            {
                                "text": "📢 Share This Group",
                                "url": "https://t.me/india_best_deals_alerts",
                            }
                        ],
                    ]
                },
            },
            error_label="Telegram Bot API",
        )
        if not payload.get("ok"):
            raise RuntimeError(f"Telegram rejected the showcase message: {payload}")
