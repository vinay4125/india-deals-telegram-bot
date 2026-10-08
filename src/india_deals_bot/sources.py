from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import quote

from .http import request_json
from .models import Deal, decimal_value


class DealSource(Protocol):
    name: str

    def fetch(self) -> list[Deal]: ...


def _first(mapping: dict[str, Any], *paths: str) -> Any:
    for path in paths:
        value: Any = mapping
        for part in path.split("."):
            if isinstance(value, dict) and part in value:
                value = value[part]
            elif isinstance(value, list) and part.isdigit() and int(part) < len(value):
                value = value[int(part)]
            else:
                value = None
                break
        if value is not None:
            return value
    return None


def _deal(
    merchant: str,
    item: dict[str, Any],
    *,
    product_id_paths: tuple[str, ...],
    title_paths: tuple[str, ...],
    url_paths: tuple[str, ...],
    sale_price_paths: tuple[str, ...],
    list_price_paths: tuple[str, ...],
    image_paths: tuple[str, ...] = (),
    availability_note_paths: tuple[str, ...] = (),
) -> Deal | None:
    product_id = str(_first(item, *product_id_paths) or "").strip()
    title = str(_first(item, *title_paths) or "").strip()
    url = str(_first(item, *url_paths) or "").strip()
    sale_price = decimal_value(_first(item, *sale_price_paths))
    list_price = decimal_value(_first(item, *list_price_paths))
    image_url = str(_first(item, *image_paths) or "").strip() or None
    availability_note = (
        str(_first(item, *availability_note_paths) or "").strip() or None
    )
    if not product_id:
        product_id = url
    if not title or not product_id or not url or sale_price is None or list_price is None:
        return None
    if not url.lower().startswith("https://"):
        return None
    return Deal(
        merchant,
        product_id,
        title,
        url,
        sale_price,
        list_price,
        image_url,
        availability_note,
    )


@dataclass(slots=True)
class JsonFeedSource:
    urls: tuple[str, ...]
    name: str = "JSON feeds"

    def fetch(self) -> list[Deal]:
        deals: list[Deal] = []
        for url in self.urls:
            payload = request_json(url)
            items = payload if isinstance(payload, list) else payload.get("deals", [])
            if not isinstance(items, list):
                raise ValueError(f"JSON feed {url} must contain a list or a 'deals' list")
            for item in items:
                if not isinstance(item, dict):
                    continue
                deal = _deal(
                    str(item.get("merchant") or "Online store"),
                    item,
                    product_id_paths=("id", "product_id"),
                    title_paths=("title",),
                    url_paths=("url",),
                    sale_price_paths=("sale_price", "price"),
                    list_price_paths=("list_price", "mrp"),
                    image_paths=("image_url",),
                    availability_note_paths=(
                        "availability_note",
                        "location_note",
                        "pincode_note",
                    ),
                )
                if deal:
                    deals.append(deal)
        return deals


@dataclass(slots=True)
class FlipkartSource:
    affiliate_id: str
    affiliate_token: str
    categories: tuple[str, ...]
    name: str = "Flipkart"

    def fetch(self) -> list[Deal]:
        headers = {
            "Fk-Affiliate-Id": self.affiliate_id,
            "Fk-Affiliate-Token": self.affiliate_token,
        }
        listing_url = (
            "https://affiliate-api.flipkart.net/affiliate/api/"
            f"{quote(self.affiliate_id, safe='')}.json"
        )
        payload = request_json(listing_url, headers=headers)
        listings = _first(payload, "apiGroups.affiliate.apiListings")
        if not isinstance(listings, dict):
            raise ValueError("Flipkart returned an unexpected API listing response")

        category_terms = tuple(term.lower() for term in self.categories)
        deals: list[Deal] = []
        for category, details in listings.items():
            if category_terms and not any(term in category.lower() for term in category_terms):
                continue
            variants = details.get("availableVariants", {}) if isinstance(details, dict) else {}
            variant = variants.get("v1.1.0") or variants.get("v0.1.0") or {}
            feed_url = variant.get("get")
            if not feed_url:
                continue
            feed = request_json(feed_url, headers=headers)
            products = feed.get("productInfoList", []) if isinstance(feed, dict) else []
            for product in products:
                if not isinstance(product, dict):
                    continue
                base = product.get("productBaseInfoV1", product)
                deal = _deal(
                    "Flipkart",
                    base,
                    product_id_paths=("productId",),
                    title_paths=("title",),
                    url_paths=("productUrl",),
                    sale_price_paths=(
                        "flipkartSpecialPrice.amount",
                        "flipkartSellingPrice.amount",
                    ),
                    list_price_paths=("maximumRetailPrice.amount",),
                    image_paths=("imageUrls.400x400", "imageUrls.200x200"),
                )
                if deal:
                    deals.append(deal)
        return deals


@dataclass(slots=True)
class AmazonCreatorsSource:
    client_id: str
    client_secret: str
    partner_tag: str
    keywords: tuple[str, ...]
    token_url: str
    api_url: str
    name: str = "Amazon India"

    def fetch(self) -> list[Deal]:
        token_payload = request_json(
            self.token_url,
            method="POST",
            form={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "creatorsapi::default",
            },
        )
        access_token = token_payload.get("access_token")
        if not access_token:
            raise ValueError("Amazon Creators API token response did not include access_token")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "x-marketplace": "www.amazon.in",
            "x-partner-tag": self.partner_tag,
        }
        deals: list[Deal] = []
        for keyword in self.keywords:
            payload = request_json(
                self.api_url,
                method="POST",
                headers=headers,
                data={
                    "keywords": keyword,
                    "resources": [
                        "itemInfo.title",
                        "images.primary.medium",
                        "offersV2.listings.price",
                        "offersV2.listings.savingBasis",
                    ],
                },
            )
            items = _first(payload, "searchResult.items", "SearchResult.Items") or []
            if not isinstance(items, list):
                raise ValueError("Amazon Creators API returned an unexpected search response")
            for item in items:
                if not isinstance(item, dict):
                    continue
                deal = _deal(
                    "Amazon India",
                    item,
                    product_id_paths=("asin", "ASIN"),
                    title_paths=(
                        "itemInfo.title.displayValue",
                        "ItemInfo.Title.DisplayValue",
                    ),
                    url_paths=("detailPageURL", "DetailPageURL"),
                    sale_price_paths=(
                        "offersV2.listings.0.price.amount",
                        "OffersV2.Listings.0.Price.Amount",
                    ),
                    list_price_paths=(
                        "offersV2.listings.0.savingBasis.amount",
                        "OffersV2.Listings.0.SavingBasis.Amount",
                    ),
                    image_paths=(
                        "images.primary.medium.url",
                        "Images.Primary.Medium.URL",
                    ),
                )
                if deal:
                    deals.append(deal)
        return deals
