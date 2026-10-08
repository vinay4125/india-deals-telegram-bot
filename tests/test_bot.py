from __future__ import annotations

import json
import os
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from india_deals_bot.app import select_deals
from india_deals_bot.config import load_env_file
from india_deals_bot.models import Deal, decimal_value
from india_deals_bot.sources import _first
from india_deals_bot.state import DealState
from india_deals_bot.telegram import format_deal


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


if __name__ == "__main__":
    unittest.main()
