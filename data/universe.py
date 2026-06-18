"""
默认行业 ETF 观察池
"""
from __future__ import annotations

from data.utils import normalise_symbol

DEFAULT_UNIVERSE = [
    {
        "symbol": "512480",
        "name": "半导体ETF",
        "board_name": "半导体",
        "board_code": "BK1036",
        "board_type": "industry",
        "theme": "科技成长",
    },
    {
        "symbol": "515790",
        "name": "光伏ETF",
        "board_name": "光伏设备",
        "board_code": "BK1031",
        "board_type": "industry",
        "theme": "新能源",
    },
    {
        "symbol": "512660",
        "name": "军工ETF",
        "board_name": "航天航空",
        "board_code": "BK0480",
        "board_type": "concept",
        "theme": "高端制造",
    },
    {
        "symbol": "512170",
        "name": "医疗ETF",
        "board_name": "医疗服务",
        "board_code": "BK0727",
        "board_type": "industry",
        "theme": "医药",
    },
    {
        "symbol": "512690",
        "name": "酒ETF",
        "board_name": "酿酒概念",
        "board_code": "BK0477",
        "board_type": "concept",
        "theme": "消费",
    },
    {
        "symbol": "512880",
        "name": "证券ETF",
        "board_name": "证券Ⅱ",
        "board_code": "BK0473",
        "board_type": "industry",
        "theme": "金融",
    },
    {
        "symbol": "515030",
        "name": "新能源车ETF",
        "board_name": "汽车整车",
        "board_code": "BK1029",
        "board_type": "concept",
        "theme": "新能源",
    },
    {
        "symbol": "515220",
        "name": "煤炭ETF",
        "board_name": "煤炭",
        "board_code": "BK0437",
        "board_type": "industry",
        "theme": "资源",
    },
    {
        "symbol": "512800",
        "name": "银行ETF",
        "board_name": "银行",
        "board_code": "BK1283",
        "board_type": "industry",
        "theme": "金融防御",
    },
    {
        "symbol": "159928",
        "name": "消费ETF",
        "board_name": "食品饮料",
        "board_code": "BK0438",
        "board_type": "industry",
        "theme": "消费",
    },
    {
        "symbol": "512400",
        "name": "有色ETF",
        "board_name": "有色金属",
        "board_code": "BK0478",
        "board_type": "industry",
        "theme": "资源",
    },
    {
        "symbol": "159819",
        "name": "人工智能ETF",
        "board_name": "人工智能",
        "board_code": "BK0800",
        "board_type": "concept",
        "theme": "科技成长",
    },
]


def default_universe() -> list[dict]:
    return [dict(item) for item in DEFAULT_UNIVERSE]


def find_universe_entry(symbol: str) -> dict | None:
    target = normalise_symbol(symbol)
    for item in DEFAULT_UNIVERSE:
        if item["symbol"] == target:
            return dict(item)
    return None


def coerce_universe_entry(symbol: str) -> dict:
    entry = find_universe_entry(symbol)
    if entry is not None:
        return entry
    code = normalise_symbol(symbol)
    return {
        "symbol": code,
        "name": f"{code} ETF",
        "board_name": "",
        "board_code": "",
        "board_type": "industry",
        "theme": "自定义",
    }
