"""
ETF 行情与历史指标
"""
from __future__ import annotations

from datetime import datetime

from data.utils import eastmoney_json, normalise_symbol, pct_change, retry_call, safe_float, to_yf_ticker


def get_etf_price_profile(symbol: str, name: str = "", spot_df=None) -> dict:
    code = normalise_symbol(symbol)
    result = {
        "symbol": code,
        "name": name or code,
    }

    quote = _load_etf_quote(code)
    if quote is not None:
        result.update(quote)

    history = _load_eastmoney_history(code)
    source = "Eastmoney ETF history"
    if history is None:
        history = _load_yfinance_history(code)
        source = "Yahoo Finance"

    if history is None:
        if len(result) <= 2:
            return {"symbol": code, "error": "无法获取 ETF 行情"}
        result["error"] = "无法获取 ETF 历史数据"
        return result

    result.update(_parse_history_frame(history, source))
    if quote is not None:
        # 实时快照优先覆盖最近一笔行情
        result["current_price"] = quote.get("current_price") or result.get("current_price")
        result["change_pct"] = quote.get("change_pct") if quote.get("change_pct") is not None else result.get("change_pct")
        result["amount"] = quote.get("amount") or result.get("amount")
        result["volume"] = quote.get("volume") or result.get("volume")
        result["source"] = "Eastmoney ETF quote + " + source
    return result


def _load_etf_quote(symbol: str) -> dict | None:
    try:
        payload = retry_call(lambda: eastmoney_json(
            "https://push2.eastmoney.com/api/qt/stock/get",
            {
                "fields": (
                    "f43,f44,f45,f46,f47,f48,f57,f58,f60,"
                    "f116,f117,f168,f169,f170,f171,f184"
                ),
                "mpi": "1000",
                "invt": "2",
                "fltt": "1",
                "secid": f"{get_market_id(symbol)}.{symbol}",
            },
        ))
    except Exception:
        return None

    data = payload.get("data") or {}
    if not data:
        return None
    return _parse_quote_payload(data)


def get_market_id(symbol: str) -> int:
    if symbol.startswith(("5", "6")):
        return 1
    return 0


def _load_eastmoney_history(symbol: str):
    import pandas as pd

    try:
        payload = retry_call(lambda: eastmoney_json(
            "https://push2his.eastmoney.com/api/qt/stock/kline/get",
            {
                "fields1": "f1,f2,f3,f4,f5,f6",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f116",
                "ut": "7eea3edcaed734bea9cbfc24409ed989",
                "klt": "101",
                "fqt": "1",
                "beg": "19700101",
                "end": "20500101",
                "secid": f"{get_market_id(symbol)}.{symbol}",
            },
        ))
    except Exception:
        return None

    klines = (payload.get("data") or {}).get("klines") or []
    if not klines:
        return None

    frame = pd.DataFrame([item.split(",") for item in klines])
    frame.columns = [
        "日期",
        "开盘",
        "收盘",
        "最高",
        "最低",
        "成交量",
        "成交额",
        "振幅",
        "涨跌幅",
        "涨跌额",
        "换手率",
    ]
    return frame


def _load_yfinance_history(symbol: str):
    try:
        import yfinance as yf
    except Exception:
        return None

    try:
        ticker = yf.Ticker(to_yf_ticker(symbol))
        history = ticker.history(period="18mo", auto_adjust=False)
        if getattr(history, "empty", True):
            return None
        return history.reset_index()
    except Exception:
        return None


def _parse_quote_payload(data: dict) -> dict:
    return {
        "quote_name": data.get("f58"),
        "current_price": _scaled_etf_price(data.get("f43")),
        "open_price": _scaled_etf_price(data.get("f46")),
        "high_price": _scaled_etf_price(data.get("f44")),
        "low_price": _scaled_etf_price(data.get("f45")),
        "prev_close": _scaled_etf_price(data.get("f60")),
        "change_pct": _scaled_pct(data.get("f170")),
        "change_amount": _scaled_etf_price(data.get("f169")),
        "amplitude_pct": _scaled_pct(data.get("f171")),
        "turnover_rate": _scaled_pct(data.get("f168")),
        "volume": safe_float(data.get("f47"), 0),
        "amount": safe_float(data.get("f48"), 0),
        "market_cap": safe_float(data.get("f116")),
        "float_market_cap": safe_float(data.get("f117")),
        "main_flow_pct": safe_float(data.get("f184")),
    }


def _parse_history_frame(df, source: str) -> dict:
    import pandas as pd

    if df is None or getattr(df, "empty", True):
        return {"error": "历史行情为空", "source": source}

    frame = df.copy()
    date_col = _pick_column(frame, ("日期", "date", "Date"))
    close_col = _pick_column(frame, ("收盘", "Close", "close", "最新价"))
    open_col = _pick_column(frame, ("开盘", "Open", "open"))
    high_col = _pick_column(frame, ("最高", "High", "high"))
    low_col = _pick_column(frame, ("最低", "Low", "low"))
    volume_col = _pick_column(frame, ("成交量", "Volume", "volume"))
    amount_col = _pick_column(frame, ("成交额", "Amount", "amount"))
    change_col = _pick_column(frame, ("涨跌幅", "change_pct", "Change"))

    if date_col is None or close_col is None:
        return {"error": "历史行情缺少日期或收盘价", "source": source}

    frame[date_col] = pd.to_datetime(frame[date_col], errors="coerce")
    frame = frame.dropna(subset=[date_col]).sort_values(date_col).reset_index(drop=True)
    close = pd.to_numeric(frame[close_col], errors="coerce")
    frame = frame[close.notna()].reset_index(drop=True)
    close = pd.to_numeric(frame[close_col], errors="coerce")
    if frame.empty:
        return {"error": "历史行情缺少有效收盘价", "source": source}

    latest_idx = len(frame) - 1
    latest_date = frame.loc[latest_idx, date_col]
    latest_price = float(close.iloc[-1])

    open_series = _numeric_series(frame, open_col)
    high_series = _numeric_series(frame, high_col)
    low_series = _numeric_series(frame, low_col)
    volume_series = _numeric_series(frame, volume_col)
    amount_series = _numeric_series(frame, amount_col)

    ma20 = _rolling_last(close, 20)
    ma60 = _rolling_last(close, 60)
    ma120 = _rolling_last(close, 120)
    high_252 = _rolling_window(close, 252, "max")
    low_252 = _rolling_window(close, 252, "min")
    returns = close.pct_change()
    latest_amount = safe_float(amount_series.iloc[-1]) if amount_series is not None and len(amount_series) > 0 else None
    latest_volume = safe_float(volume_series.iloc[-1]) if volume_series is not None and len(volume_series) > 0 else None

    result = {
        "source": source,
        "last_date": latest_date.strftime("%Y-%m-%d") if isinstance(latest_date, datetime) else str(latest_date),
        "current_price": round(latest_price, 3),
        "open_price": safe_float(open_series.iloc[-1]) if open_series is not None else None,
        "high_price": safe_float(high_series.iloc[-1]) if high_series is not None else None,
        "low_price": safe_float(low_series.iloc[-1]) if low_series is not None else None,
        "change_pct": safe_float(frame.loc[latest_idx, change_col]) if change_col else pct_change(latest_price, close.iloc[-2] if len(close) > 1 else None),
        "return_5d": _window_return(close, 5),
        "return_20d": _window_return(close, 20),
        "return_60d": _window_return(close, 60),
        "return_ytd": _ytd_return(frame, date_col, close),
        "ma20": ma20,
        "ma60": ma60,
        "ma120": ma120,
        "price_vs_ma20_pct": pct_change(latest_price, ma20),
        "price_vs_ma60_pct": pct_change(latest_price, ma60),
        "price_vs_ma120_pct": pct_change(latest_price, ma120),
        "high_52w": high_252,
        "low_52w": low_252,
        "drawdown_from_52w_high_pct": pct_change(latest_price, high_252),
        "volatility_20d": _annualised_volatility(returns, 20),
        "volatility_60d": _annualised_volatility(returns, 60),
        "volume": latest_volume,
        "amount": latest_amount,
        "volume_ratio_20d": _latest_ratio(volume_series, 20),
        "amount_ratio_20d": _latest_ratio(amount_series, 20),
    }
    return result


def _pick_column(frame, aliases: tuple[str, ...]) -> str | None:
    for alias in aliases:
        if alias in getattr(frame, "columns", []):
            return alias
    return None


def _numeric_series(frame, column: str | None):
    import pandas as pd

    if column is None:
        return None
    return pd.to_numeric(frame[column], errors="coerce")


def _rolling_last(series, window: int) -> float | None:
    if len(series) < window:
        return None
    return safe_float(series.rolling(window).mean().iloc[-1], 3)


def _rolling_window(series, window: int, method: str) -> float | None:
    if len(series) == 0:
        return None
    tail = series.tail(window) if len(series) >= window else series
    if method == "max":
        return safe_float(tail.max(), 3)
    return safe_float(tail.min(), 3)


def _window_return(series, window: int) -> float | None:
    if len(series) <= window:
        return None
    base = series.iloc[-window - 1]
    latest = series.iloc[-1]
    return pct_change(latest, base)


def _annualised_volatility(returns, window: int) -> float | None:
    if len(returns) <= window:
        return None
    sample = returns.tail(window).dropna()
    if len(sample) < max(5, window // 2):
        return None
    return safe_float(sample.std() * (252 ** 0.5) * 100, 1)


def _latest_ratio(series, window: int) -> float | None:
    if series is None or len(series) <= window:
        return None
    latest = series.iloc[-1]
    baseline = series.iloc[-window - 1:-1].dropna()
    if len(baseline) == 0:
        return None
    return safe_float(latest / baseline.mean(), 2)


def _ytd_return(frame, date_col: str, close) -> float | None:
    year = datetime.now().year
    ytd_frame = frame[frame[date_col].dt.year == year]
    if len(ytd_frame) < 2:
        return None
    ytd_close = close.loc[ytd_frame.index]
    return pct_change(ytd_close.iloc[-1], ytd_close.iloc[0])


def _scaled_price(value) -> float | None:
    number = safe_float(value, 4)
    if number is None:
        return None
    return round(number / 100, 3)


def _scaled_etf_price(value) -> float | None:
    number = safe_float(value, 4)
    if number is None:
        return None
    return round(number / 1000, 3)


def _scaled_pct(value) -> float | None:
    number = safe_float(value, 4)
    if number is None:
        return None
    return round(number / 100, 2)
