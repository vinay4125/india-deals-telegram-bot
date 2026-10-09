from __future__ import annotations

import os
import sys
from decimal import Decimal

from .config import Settings, load_env_file
from .models import Deal, decimal_value
from .telegram import TelegramClient


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} is required")
    return value


def deal_from_env() -> Deal:
    merchant = _required("DEAL_MERCHANT")
    title = _required("DEAL_TITLE")
    url = _required("DEAL_URL")
    if not url.lower().startswith("https://"):
        raise ValueError("DEAL_URL must be an HTTPS URL")

    sale_price = decimal_value(_required("DEAL_SALE_PRICE"))
    list_price = decimal_value(_required("DEAL_LIST_PRICE"))
    if sale_price is None or sale_price <= 0:
        raise ValueError("DEAL_SALE_PRICE must be greater than zero")
    if list_price is None or list_price <= 0:
        raise ValueError("DEAL_LIST_PRICE must be greater than zero")
    if sale_price > list_price:
        raise ValueError("DEAL_SALE_PRICE cannot exceed DEAL_LIST_PRICE")

    image_url = os.getenv("DEAL_IMAGE_URL", "").strip() or None
    if image_url and not image_url.lower().startswith("https://"):
        raise ValueError("DEAL_IMAGE_URL must be an HTTPS URL")

    product_id = os.getenv("DEAL_PRODUCT_ID", "").strip() or url
    availability_note = os.getenv("DEAL_AVAILABILITY_NOTE", "").strip() or None
    return Deal(
        merchant=merchant,
        product_id=product_id,
        title=title,
        url=url,
        sale_price=sale_price,
        list_price=list_price,
        image_url=image_url,
        availability_note=availability_note,
    )


def main() -> int:
    try:
        load_env_file()
        settings = Settings.from_env()
        TelegramClient(
            settings.telegram_bot_token, settings.telegram_chat_id
        ).send_deal(deal_from_env())
    except (RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print("Posted manual deal")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
