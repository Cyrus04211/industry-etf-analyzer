from __future__ import annotations

import unittest

from data.industry import _parse_board_spot_row
from data.price import _parse_quote_payload
from data.universe import coerce_universe_entry, find_universe_entry


class DataParserTests(unittest.TestCase):
    def test_parse_etf_quote_payload_scales_eastmoney_fields(self):
        payload = {
            "f43": 2470,
            "f44": 2477,
            "f45": 2377,
            "f46": 2384,
            "f47": 5138944,
            "f48": 1249948743.0,
            "f58": "半导体ETF国联安",
            "f60": 2387,
            "f116": 20631918694.4,
            "f117": 20631918694.4,
            "f168": 615,
            "f169": 83,
            "f170": 348,
            "f171": 419,
            "f184": "-",
        }
        parsed = _parse_quote_payload(payload)
        self.assertEqual(parsed["quote_name"], "半导体ETF国联安")
        self.assertEqual(parsed["current_price"], 2.47)
        self.assertEqual(parsed["open_price"], 2.384)
        self.assertEqual(parsed["change_pct"], 3.48)
        self.assertEqual(parsed["turnover_rate"], 6.15)
        self.assertEqual(parsed["change_amount"], 0.083)
        self.assertEqual(parsed["volume"], 5138944)

    def test_parse_board_spot_row_extracts_breadth_and_leader(self):
        row = {
            "f2": 1265.23,
            "f3": 2.14,
            "f8": 3.66,
            "f104": 38,
            "f105": 12,
            "f128": "北方华创",
            "f136": 5.83,
        }
        parsed = _parse_board_spot_row(row)
        self.assertEqual(parsed["current_level"], 1265.23)
        self.assertEqual(parsed["change_pct"], 2.14)
        self.assertEqual(parsed["up_count"], 38)
        self.assertEqual(parsed["down_count"], 12)
        self.assertAlmostEqual(parsed["positive_ratio"], 0.76, places=2)
        self.assertEqual(parsed["leader_name"], "北方华创")
        self.assertEqual(parsed["leader_change_pct"], 5.83)

    def test_default_universe_entry_contains_board_metadata(self):
        entry = coerce_universe_entry("512480")
        self.assertEqual(entry["board_code"], "BK1036")
        self.assertEqual(entry["board_type"], "industry")

    def test_find_universe_entry_returns_none_for_unknown(self):
        self.assertIsNone(find_universe_entry("999999"))

    def test_coerce_unknown_symbol_returns_fallback(self):
        entry = coerce_universe_entry("999999")
        self.assertEqual(entry["symbol"], "999999")
        self.assertEqual(entry["theme"], "自定义")


class ResolverTests(unittest.TestCase):
    def test_build_single_etf_context_handles_minimal_input(self):
        from data.resolver import build_single_etf_context
        payload = {
            "symbol": "512480",
            "name": "测试ETF",
            "theme": "测试",
            "board_name": "测试板块",
            "etf": {"current_price": 1.0, "source": "test"},
            "industry": {},
            "market": {"regime": "neutral", "broad_benchmark": {}},
            "macro": {},
            "sentiment": {},
            "news": {"items": [], "freshness": {}},
            "derived": {},
        }
        ctx = build_single_etf_context(payload)
        self.assertIn("512480", ctx)
        self.assertIn("测试ETF", ctx)

    def test_build_universe_context_handles_empty_analyses(self):
        from data.resolver import build_universe_context
        bundle = {
            "market": {"regime": "neutral", "broad_benchmark": {}},
            "macro": {},
            "sentiment": {},
            "analyses": [],
        }
        ctx = build_universe_context(bundle)
        self.assertIn("neutral", ctx)


class FreshnessTests(unittest.TestCase):
    def test_parse_item_date_handles_iso_format(self):
        from data.freshness import parse_item_date
        from datetime import date
        result = parse_item_date("2026-06-15")
        self.assertEqual(result, date(2026, 6, 15))

    def test_parse_item_date_handles_none(self):
        from data.freshness import parse_item_date
        self.assertIsNone(parse_item_date(None))
        self.assertIsNone(parse_item_date(""))
        self.assertIsNone(parse_item_date("nan"))

    def test_freshness_filter_drops_old_items(self):
        from data.freshness import filter_items_by_freshness
        items = [
            {"title": "fresh", "date": "2099-01-01"},
            {"title": "stale", "date": "2020-01-01"},
            {"title": "unknown", "info": "no date"},
        ]
        fresh, meta = filter_items_by_freshness(items, ("date",), max_age_days=7)
        # "fresh" has date in 2099 which is in the future, should be kept
        # "stale" has date in 2020, should be dropped
        self.assertEqual(len(fresh), 1)
        self.assertEqual(fresh[0]["title"], "fresh")
        self.assertEqual(meta["stale_dropped"], 1)


if __name__ == "__main__":
    unittest.main()
