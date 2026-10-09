from __future__ import annotations

import json
import os
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from india_deals_bot.app import select_deals
from india_deals_bot.config import load_env_file
from india_deals_bot.manual_deal import deal_from_env
from india_deals_bot.models import Deal, decimal_value
from india_deals_bot.sources import _first
from india_deals_bot.state import DealState
from india_deals_bot.telegram import TelegramClient, format_deal


class DealTests(unittest.TestCase):
    def test_discount_and_decimal_parsing(self) -> None:
        deal = Deal(
            "Store",
            "123",
            "Laptop",
            "https://example.com/product",
            Decimal("60000"),
            Decimal("80000"),
        )
        self.assertEqual(deal.discount_percent, Decimal("25.0"))
        self.assertEqual(decimal_value("₹1,299.50"), Decimal("1299.50"))

    def test_selects_ranked_unseen_matching_deals(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state = DealState(Path(directory) / "state.json", 14)
            seen = Deal(
                "Store",
                "seen",
                "Laptop seen",
                "https://example.com/seen",
                Decimal("50"),
                Decimal("100"),
            )
            state.mark(seen.key)
            deals = [
                seen,
                Deal(
                    "Store",
                    "best",
                    "Laptop best",
                    "https://example.com/best",
                    Decimal("30"),
                    Decimal("100"),
                ),
                Deal(
                    "Store",
                    "low",
                    "Laptop low",
                    "https://example.com/low",
                    Decimal("80"),
                    Decimal("100"),
                ),
                Deal(
                    "Store",
                    "wrong-keyword",
                    "Shoes",
                    "https://example.com/shoes",
                    Decimal("20"),
                    Decimal("100"),
                ),
            ]
            selected = select_deals(
                deals,
                minimum_discount=Decimal("30"),
                keywords=("laptop",),
                state=state,
                limit=10,
            )
            self.assertEqual([deal.product_id for deal in selected], ["best"])

    def test_state_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            state = DealState(path, 14)
            state.mark("abc")
            state.save()
            self.assertTrue(DealState(path, 14).contains("abc"))
            self.assertEqual(json.loads(path.read_text())["abc"][-6:], "+00:00")

    def test_telegram_html_is_escaped(self) -> None:
        deal = Deal(
            "A&B",
            "1",
            "<Great> Laptop",
            "https://example.com/?a=1&b=2",
            Decimal("50"),
            Decimal("100"),
        )
        message = format_deal(deal)
        self.assertIn("&lt;Great&gt;", message)
        self.assertIn("A&amp;B", message)
        self.assertIn("a=1&amp;b=2", message)

    def test_nested_list_paths_are_supported(self) -> None:
        payload = {"offers": {"listings": [{"price": {"amount": 499}}]}}
        self.assertEqual(_first(payload, "offers.listings.0.price.amount"), 499)

    def test_flash_deals_rank_before_larger_discounts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state = DealState(Path(directory) / "state.json", 14)
            regular = Deal(
                "Store",
                "regular",
                "Regular deal",
                "https://example.com/regular",
                Decimal("100"),
                Decimal("1000"),
            )
            flash = Deal(
                "Blinkit",
                "flash",
                "One rupee deal",
                "https://example.com/flash",
                Decimal("1"),
                Decimal("10"),
                availability_note="Selected pincodes only",
            )
            selected = select_deals(
                [regular, flash],
                minimum_discount=Decimal("30"),
                keywords=(),
                state=state,
                limit=10,
                flash_deal_max_price=Decimal("10"),
            )
            self.assertEqual([deal.product_id for deal in selected], ["flash", "regular"])
            message = format_deal(flash)
            self.assertIn("₹1 / FLASH DEAL", message)
            self.assertIn("Selected pincodes only", message)

    def test_loads_env_without_overriding_existing_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("NEW_TEST_VALUE=loaded\nEXISTING_TEST_VALUE=file\n")
            os.environ["EXISTING_TEST_VALUE"] = "process"
            os.environ.pop("NEW_TEST_VALUE", None)
            try:
                load_env_file(path)
                self.assertEqual(os.environ["NEW_TEST_VALUE"], "loaded")
                self.assertEqual(os.environ["EXISTING_TEST_VALUE"], "process")
            finally:
                os.environ.pop("NEW_TEST_VALUE", None)
                os.environ.pop("EXISTING_TEST_VALUE", None)

    @patch("india_deals_bot.telegram.request_json")
    def test_sends_image_deal_with_inline_button(self, request_json_mock) -> None:
        request_json_mock.return_value = {"ok": True}
        deal = Deal(
            "Amazon India",
            "image",
            "Headphones",
            "https://example.com/deal",
            Decimal("999"),
            Decimal("1999"),
            image_url="https://example.com/image.jpg",
        )
        TelegramClient("token", "-1001").send_deal(deal)
        args, kwargs = request_json_mock.call_args
        self.assertTrue(args[0].endswith("/sendPhoto"))
        self.assertEqual(kwargs["data"]["photo"], deal.image_url)
        button = kwargs["data"]["reply_markup"]["inline_keyboard"][0][0]
        self.assertEqual(button["url"], deal.url)

    def test_builds_valid_manual_deal(self) -> None:
        values = {
            "DEAL_MERCHANT": "Amazon India",
            "DEAL_TITLE": "Example product",
            "DEAL_SALE_PRICE": "999",
            "DEAL_LIST_PRICE": "1999",
            "DEAL_URL": "https://example.com/product",
            "DEAL_IMAGE_URL": "https://example.com/image.jpg",
            "DEAL_AVAILABILITY_NOTE": "Selected cards only",
        }
        with patch.dict(os.environ, values, clear=False):
            deal = deal_from_env()
        self.assertEqual(deal.sale_price, Decimal("999"))
        self.assertEqual(deal.discount_percent, Decimal("50.0"))
        self.assertEqual(deal.availability_note, "Selected cards only")

    def test_rejects_invalid_manual_prices(self) -> None:
        values = {
            "DEAL_MERCHANT": "Store",
            "DEAL_TITLE": "Invalid product",
            "DEAL_SALE_PRICE": "200",
            "DEAL_LIST_PRICE": "100",
            "DEAL_URL": "https://example.com/product",
        }
        with patch.dict(os.environ, values, clear=False):
            with self.assertRaisesRegex(ValueError, "cannot exceed"):
                deal_from_env()


if __name__ == "__main__":
    unittest.main()
