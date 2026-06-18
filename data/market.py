"""
市场环境与风格轮动背景
"""
from __future__ import annotations

import concurrent.futures

from data.price import get_etf_price_profile

BENCHMARKS = [
    {"symbol": "510300", "name": "沪深300ETF"},
    {"symbol": "510050", "name": "上证50ETF"},
    {"symbol": "159915", "name": "创业板ETF"},
    {"symbol": "512100", "name": "中证1000ETF"},
]


def get_market_context() -> dict:
    benchmark_data = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(BENCHMARKS)) as executor:
        futures = {
            executor.submit(get_etf_price_profile, item["symbol"], item["name"]): item
            for item in BENCHMARKS
        }
        for future in concurrent.futures.as_completed(futures):
            item = futures[future]
            try:
                benchmark_data[item["symbol"]] = future.result()
            except Exception as exc:
                benchmark_data[item["symbol"]] = {
                    "symbol": item["symbol"],
                    "name": item["name"],
                    "error": str(exc),
                }

    broad = benchmark_data.get("510300", {})
    growth = benchmark_data.get("159915", {})
    value = benchmark_data.get("510050", {})

    growth_spread_20d = _diff(growth.get("return_20d"), value.get("return_20d"))
    growth_spread_60d = _diff(growth.get("return_60d"), value.get("return_60d"))

    regime = "neutral"
    if _gt(broad.get("current_price"), broad.get("ma20")) and _gt(broad.get("current_price"), broad.get("ma60")):
        regime = "risk_on"
    elif _lt(broad.get("current_price"), broad.get("ma20")) and _lt(broad.get("current_price"), broad.get("ma60")):
        regime = "risk_off"

    if regime == "neutral":
        summary = "主指数处于震荡区间，行业轮动更依赖相对强弱。"
    elif regime == "risk_on":
        summary = "主指数站上中短期均线，风险偏好回暖，顺势行业更容易延续。"
    else:
        summary = "主指数弱于中短期均线，防御或低波行业通常更占优。"

    return {
        "regime": regime,
        "summary": summary,
        "benchmarks": benchmark_data,
        "broad_benchmark": broad,
        "growth_vs_value": {
            "spread_20d": growth_spread_20d,
            "spread_60d": growth_spread_60d,
        },
    }


def _diff(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return round(left - right, 1)


def _gt(left: float | None, right: float | None) -> bool:
    return left is not None and right is not None and left > right


def _lt(left: float | None, right: float | None) -> bool:
    return left is not None and right is not None and left < right
