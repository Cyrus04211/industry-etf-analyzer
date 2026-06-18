from __future__ import annotations

import unittest

from data.industry import _parse_board_spot_row
from data.price import _parse_quote_payload
from data.universe import coerce_universe_entry


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
        self.assertEqual(parsed["positive_ratio"], 0.76)
        self.assertEqual(parsed["leader_name"], "北方华创")
        self.assertEqual(parsed["leader_change_pct"], 5.83)

    def test_default_universe_entry_contains_board_metadata(self):
        entry = coerce_universe_entry("512480")
        self.assertEqual(entry["board_code"], "BK1036")
        self.assertEqual(entry["board_type"], "industry")


if __name__ == "__main__":
    unittest.main()
