from __future__ import annotations

import unittest

from strategy.scoring import compute_recommendation, rank_analyses


class ScoringTests(unittest.TestCase):
    def test_strong_trend_receives_positive_rating(self):
        payload = {
            "etf": {
                "current_price": 1.35,
                "ma20": 1.26,
                "ma60": 1.18,
                "ma120": 1.09,
                "return_20d": 10.0,
                "return_60d": 18.0,
                "volume_ratio_20d": 1.4,
                "amount_ratio_20d": 1.3,
                "turnover_rate": 2.3,
                "volatility_20d": 18.0,
                "drawdown_from_52w_high_pct": -4.0,
            },
            "industry": {
                "positive_ratio": 0.72,
                "change_pct": 1.8,
                "return_20d": 8.5,
            },
            "market": {
                "regime": "risk_on",
                "broad_benchmark": {
                    "return_20d": 3.0,
                    "return_60d": 7.0,
                },
            },
        }
        rec = compute_recommendation(payload)
        self.assertGreaterEqual(rec["total_score"], 75)
        self.assertEqual(rec["rating"], "积极关注")
        self.assertEqual(rec["position_size"], "高")

    def test_weak_trend_receives_avoid_rating(self):
        payload = {
            "etf": {
                "current_price": 0.92,
                "ma20": 0.98,
                "ma60": 1.02,
                "ma120": 1.08,
                "return_20d": -8.0,
                "return_60d": -15.0,
                "volume_ratio_20d": 0.7,
                "amount_ratio_20d": 0.8,
                "turnover_rate": 0.9,
                "volatility_20d": 31.0,
                "drawdown_from_52w_high_pct": -24.0,
            },
            "industry": {
                "positive_ratio": 0.32,
                "change_pct": -1.9,
                "return_20d": -7.2,
            },
            "market": {
                "regime": "risk_off",
                "broad_benchmark": {
                    "return_20d": -2.0,
                    "return_60d": -4.0,
                },
            },
        }
        rec = compute_recommendation(payload)
        self.assertLess(rec["total_score"], 45)
        self.assertEqual(rec["rating"], "暂避")
        self.assertEqual(rec["position_size"], "零")

    def test_rank_analyses_orders_by_total_score(self):
        items = [
            {"symbol": "A", "recommendation": {"total_score": 54}},
            {"symbol": "B", "recommendation": {"total_score": 81}},
            {"symbol": "C", "recommendation": {"total_score": 63}},
        ]
        ranked = rank_analyses(items)
        self.assertEqual([item["symbol"] for item in ranked], ["B", "C", "A"])
        self.assertEqual([item["rank"] for item in ranked], [1, 2, 3])


if __name__ == "__main__":
    unittest.main()
