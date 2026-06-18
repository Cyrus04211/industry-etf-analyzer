"""
数据层通用工具
"""
from __future__ import annotations

import math
import re
import time
import json
from datetime import datetime, timedelta
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from typing import Any, Callable, Iterable, TypeVar

T = TypeVar("T")

EASTMONEY_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Referer": "https://quote.eastmoney.com/",
}


def safe_float(value: Any, digits: int = 2) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return round(number, digits)


def safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return int(number)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def pct_change(current: float | None, base: float | None, digits: int = 1) -> float | None:
    if current in (None, 0) or base in (None, 0):
        return None
    return round((float(current) / float(base) - 1) * 100, digits)


def choose_first(mapping: Any, aliases: Iterable[str]) -> Any:
    if mapping is None:
        return None
    for alias in aliases:
        if hasattr(mapping, "__contains__") and alias in mapping:
            value = mapping[alias]
            if value not in (None, "", "-", "--"):
                return value
    return None


def retry_call(fn: Callable[[], T], retries: int = 2, delay: float = 1.0) -> T:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return fn()
        except Exception as exc:  # pragma: no cover - 重试分支依赖外部数据源
            last_error = exc
            if attempt < retries:
                time.sleep(delay * (attempt + 1))
    assert last_error is not None
    raise last_error


def eastmoney_json(url: str, params: dict[str, Any], timeout: float = 15.0) -> dict:
    query = urlencode(params)
    request = Request(f"{url}?{query}", headers=EASTMONEY_HEADERS)
    with urlopen(request, timeout=timeout) as response:
        return json.load(response)


def normalise_symbol(symbol: str) -> str:
    text = re.sub(r"\D", "", str(symbol or ""))
    if len(text) == 6:
        return text
    return str(symbol or "").strip().upper()


def to_yf_ticker(symbol: str) -> str:
    code = normalise_symbol(symbol)
    if len(code) == 6 and code.isdigit():
        if code.startswith("159"):
            return f"{code}.SZ"
        return f"{code}.SS"
    return code


def recent_cutoff(days: int) -> datetime:
    return datetime.now() - timedelta(days=days)


def parse_any_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None

    formats = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%m-%d %H:%M",
    )
    for fmt in formats:
        try:
            parsed = datetime.strptime(text, fmt)
            if fmt == "%m-%d %H:%M":
                return parsed.replace(year=datetime.now().year)
            return parsed
        except ValueError:
            continue
    return None


def compact_number(value: float | int | None) -> str:
    if value is None:
        return "数据不可用"
    number = float(value)
    abs_number = abs(number)
    if abs_number >= 1_000_000_000:
        return f"{number / 1_000_000_000:.2f}B"
    if abs_number >= 100_000_000:
        return f"{number / 100_000_000:.2f}亿"
    if abs_number >= 10_000:
        return f"{number / 10_000:.2f}万"
    if number.is_integer():
        return str(int(number))
    return f"{number:.2f}"
