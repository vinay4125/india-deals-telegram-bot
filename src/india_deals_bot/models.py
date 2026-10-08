from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from typing import Any


def decimal_value(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, dict):
        value = value.get("amount") or value.get("Amount") or value.get("value")
    try:
        result = Decimal(str(value).replace(",", "").replace("₹", "").strip())
    except (InvalidOperation, ValueError):
        return None
    return result if result >= 0 else None


@dataclass(frozen=True, slots=True)
class Deal:
    merchant: str
    product_id: str
    title: str
    url: str
    sale_price: Decimal
    list_price: Decimal
    image_url: str | None = None

    @property
    def discount_percent(self) -> Decimal:
        if self.list_price <= 0 or self.sale_price >= self.list_price:
            return Decimal(0)
        return ((self.list_price - self.sale_price) / self.list_price * 100).quantize(
            Decimal("0.1")
        )

    @property
    def key(self) -> str:
        identity = f"{self.merchant}|{self.product_id or self.url}".encode()
        return sha256(identity).hexdigest()
