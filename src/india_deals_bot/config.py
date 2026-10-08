from __future__ import annotations

import os
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path


def load_env_file(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"{path}:{line_number} must use NAME=value syntax")
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            raise ValueError(f"{path}:{line_number} has an invalid variable name")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ.setdefault(name, value)


def _csv(name: str, default: str = "") -> tuple[str, ...]:
    return tuple(value.strip() for value in os.getenv(name, default).split(",") if value.strip())


def _integer(name: str, default: int, minimum: int = 1) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from exc
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return value


def _decimal(name: str, default: str) -> Decimal:
    raw = os.getenv(name, default)
    try:
        value = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError(f"{name} must be a number, got {raw!r}") from exc
    if not Decimal(0) <= value <= Decimal(100):
        raise ValueError(f"{name} must be between 0 and 100")
    return value


def _boolean(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, str(default)).strip().lower()
    if raw not in {"true", "false", "1", "0", "yes", "no"}:
        raise ValueError(f"{name} must be true or false")
    return raw in {"true", "1", "yes"}


@dataclass(frozen=True, slots=True)
class Settings:
    telegram_bot_token: str
    telegram_chat_id: str
    min_discount_percent: Decimal
    max_deals_per_run: int
    state_file: Path
    state_retention_days: int
    dry_run: bool
    deal_keywords: tuple[str, ...]
    amazon_client_id: str
    amazon_client_secret: str
    amazon_partner_tag: str
    amazon_search_keywords: tuple[str, ...]
    amazon_token_url: str
    amazon_api_url: str
    flipkart_affiliate_id: str
    flipkart_affiliate_token: str
    flipkart_categories: tuple[str, ...]
    json_feed_urls: tuple[str, ...]

    @classmethod
    def from_env(cls) -> "Settings":
        dry_run = _boolean("DRY_RUN")
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
        if not dry_run and (not token or not chat_id):
            raise ValueError(
                "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required unless DRY_RUN=true"
            )
        return cls(
            telegram_bot_token=token,
            telegram_chat_id=chat_id,
            min_discount_percent=_decimal("MIN_DISCOUNT_PERCENT", "30"),
            max_deals_per_run=_integer("MAX_DEALS_PER_RUN", 10),
            state_file=Path(os.getenv("STATE_FILE", ".deals-state.json")),
            state_retention_days=_integer("STATE_RETENTION_DAYS", 14),
            dry_run=dry_run,
            deal_keywords=tuple(value.lower() for value in _csv("DEAL_KEYWORDS")),
            amazon_client_id=os.getenv("AMAZON_CREATORS_CLIENT_ID", "").strip(),
            amazon_client_secret=os.getenv("AMAZON_CREATORS_CLIENT_SECRET", "").strip(),
            amazon_partner_tag=os.getenv("AMAZON_ASSOCIATE_TAG", "").strip(),
            amazon_search_keywords=_csv(
                "AMAZON_SEARCH_KEYWORDS",
                "smartphone,laptop,headphones,television,appliances",
            ),
            amazon_token_url=os.getenv(
                "AMAZON_TOKEN_URL", "https://api.amazon.co.uk/auth/o2/token"
            ).strip(),
            amazon_api_url=os.getenv(
                "AMAZON_API_URL", "https://creatorsapi.amazon/searchItems"
            ).strip(),
            flipkart_affiliate_id=os.getenv("FLIPKART_AFFILIATE_ID", "").strip(),
            flipkart_affiliate_token=os.getenv("FLIPKART_AFFILIATE_TOKEN", "").strip(),
            flipkart_categories=_csv(
                "FLIPKART_CATEGORIES",
                "mobiles,laptops,televisions,home-appliances",
            ),
            json_feed_urls=_csv("JSON_FEED_URLS"),
        )
