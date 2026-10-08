from __future__ import annotations

import sys
from collections.abc import Iterable
from decimal import Decimal

from .config import Settings, load_env_file
from .models import Deal
from .sources import AmazonCreatorsSource, DealSource, FlipkartSource, JsonFeedSource
from .state import DealState
from .telegram import TelegramClient, format_deal


def build_sources(settings: Settings) -> list[DealSource]:
    sources: list[DealSource] = []
    amazon_values = (
        settings.amazon_client_id,
        settings.amazon_client_secret,
        settings.amazon_partner_tag,
    )
    if any(amazon_values):
        if not all(amazon_values):
            raise ValueError(
                "Amazon requires AMAZON_CREATORS_CLIENT_ID, "
                "AMAZON_CREATORS_CLIENT_SECRET, and AMAZON_ASSOCIATE_TAG"
            )
        sources.append(
            AmazonCreatorsSource(
                settings.amazon_client_id,
                settings.amazon_client_secret,
                settings.amazon_partner_tag,
                settings.amazon_search_keywords,
                settings.amazon_token_url,
                settings.amazon_api_url,
            )
        )

    flipkart_values = (settings.flipkart_affiliate_id, settings.flipkart_affiliate_token)
    if any(flipkart_values):
        if not all(flipkart_values):
            raise ValueError(
                "Flipkart requires FLIPKART_AFFILIATE_ID and FLIPKART_AFFILIATE_TOKEN"
            )
        sources.append(
            FlipkartSource(
                settings.flipkart_affiliate_id,
                settings.flipkart_affiliate_token,
                settings.flipkart_categories,
            )
        )
    if settings.json_feed_urls:
        sources.append(JsonFeedSource(settings.json_feed_urls))
    if not sources:
        raise ValueError(
            "No deal source is configured. Add Amazon/Flipkart credentials or JSON_FEED_URLS."
        )
    return sources


def select_deals(
    deals: Iterable[Deal],
    *,
    minimum_discount: Decimal,
    keywords: tuple[str, ...],
    state: DealState,
    limit: int,
    flash_deal_max_price: Decimal = Decimal("10"),
) -> list[Deal]:
    unique: dict[str, Deal] = {}
    for deal in deals:
        title = deal.title.lower()
        if deal.discount_percent < minimum_discount:
            continue
        if keywords and not any(keyword in title for keyword in keywords):
            continue
        if state.contains(deal.key):
            continue
        existing = unique.get(deal.key)
        if existing is None or deal.discount_percent > existing.discount_percent:
            unique[deal.key] = deal
    return sorted(
        unique.values(),
        key=lambda deal: (
            deal.sale_price <= flash_deal_max_price,
            deal.discount_percent,
            deal.list_price - deal.sale_price,
        ),
        reverse=True,
    )[:limit]


def run(settings: Settings) -> int:
    all_deals: list[Deal] = []
    failures: list[str] = []
    successful_sources = 0
    for source in build_sources(settings):
        try:
            source_deals = source.fetch()
        except (RuntimeError, ValueError) as exc:
            failures.append(f"{source.name}: {exc}")
            continue
        successful_sources += 1
        all_deals.extend(source_deals)

    for failure in failures:
        print(f"Source error: {failure}", file=sys.stderr)
    if not successful_sources:
        raise RuntimeError("All configured deal sources failed")

    state = DealState(settings.state_file, settings.state_retention_days)
    selected = select_deals(
        all_deals,
        minimum_discount=settings.min_discount_percent,
        keywords=settings.deal_keywords,
        state=state,
        limit=settings.max_deals_per_run,
        flash_deal_max_price=settings.flash_deal_max_price,
    )
    if settings.dry_run:
        for deal in selected:
            print(format_deal(deal))
            print("-" * 60)
        print(f"Dry run: selected {len(selected)} of {len(all_deals)} fetched deals")
        return 0

    telegram = TelegramClient(settings.telegram_bot_token, settings.telegram_chat_id)
    for deal in selected:
        telegram.send_deal(deal)
        state.mark(deal.key)
        state.save()
    print(f"Posted {len(selected)} new deals from {len(all_deals)} fetched deals")
    return 0


def main() -> int:
    try:
        load_env_file()
        return run(Settings.from_env())
    except (RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
