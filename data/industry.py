"""
行业板块数据
"""
from __future__ import annotations

from data.utils import eastmoney_json, pct_change, retry_call, safe_float, safe_int


def fetch_board_panel(board_type: str = "industry"):
    fs = _board_fs(board_type)
    host = _board_list_host(board_type)
    page = 1
    items = []

    while True:
        try:
            payload = retry_call(lambda: eastmoney_json(
                host,
                {
                    "pn": str(page),
                    "pz": "100",
                    "po": "1",
                    "np": "1",
                    "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                    "fltt": "2",
                    "invt": "2",
                    "fid": "f12",
                    "fs": fs,
                    "fields": "f2,f3,f8,f12,f14,f104,f105,f128,f136",
                },
            ))
        except Exception:
            return None

        diff = (payload.get("data") or {}).get("diff") or []
        if not diff:
            break
        items.extend(diff)
        if len(diff) < 100:
            break
        page += 1

    if not items:
        return None
    return items


def get_industry_profile(
    board_name: str,
    board_df=None,
    board_code: str = "",
    board_type: str = "industry",
    include_history: bool = False,
    include_constituents: bool = False,
) -> dict:
    if not board_name and not board_code:
        return {"board_name": "", "error": "未配置对应行业板块"}

    resolved_code = board_code or _find_board_code(board_name, board_df)
    result = {
        "board_name": board_name,
        "board_code": resolved_code,
        "board_type": board_type,
        "source": "Eastmoney board quote",
    }

    board_row = _find_board_row(resolved_code, board_df)
    if board_row is not None:
        result.update(_parse_board_spot_row(board_row))

    if resolved_code:
        spot = _load_board_spot(resolved_code)
        if spot is not None:
            result.update(spot)

    if include_history:
        history = _load_board_history(resolved_code)
        if history is not None:
            result.update(_parse_board_history(history))

    if include_constituents:
        constituents = _load_constituents(resolved_code)
        if constituents is not None:
            result.update(_parse_constituents(constituents))

    if len(result) <= 4:
        result["error"] = "无法获取行业板块数据"
    return result


def _find_board_row(board_code: str, board_df):
    if not board_code or not board_df:
        return None
    for item in board_df:
        if str(item.get("f12") or "") == board_code:
            return item
    return None


def _find_board_code(board_name: str, board_df) -> str:
    if not board_name or not board_df:
        return ""
    for item in board_df:
        name = str(item.get("f14") or "")
        if name == board_name:
            return str(item.get("f12") or "")
    for item in board_df:
        name = str(item.get("f14") or "")
        if board_name in name:
            return str(item.get("f12") or "")
    return ""


def _load_board_spot(board_code: str) -> dict | None:
    if not board_code:
        return None
    try:
        payload = retry_call(lambda: eastmoney_json(
            "https://91.push2.eastmoney.com/api/qt/stock/get",
            {
                "fields": "f43,f44,f45,f46,f47,f48,f170,f171,f168,f169",
                "mpi": "1000",
                "invt": "2",
                "fltt": "1",
                "secid": f"90.{board_code}",
            },
        ))
    except Exception:
        return None

    data = payload.get("data") or {}
    if not data:
        return None
    return {
        "current_level": _scaled_price(data.get("f43")),
        "change_pct": _scaled_pct(data.get("f170")),
        "turnover": safe_float(data.get("f48"), 0),
        "open_level": _scaled_price(data.get("f46")),
        "high_level": _scaled_price(data.get("f44")),
        "low_level": _scaled_price(data.get("f45")),
        "amplitude_pct": _scaled_pct(data.get("f171")),
        "turnover_rate": _scaled_pct(data.get("f168")),
        "change_amount": _scaled_price(data.get("f169")),
        "volume": safe_float(data.get("f47"), 0),
    }


def _load_board_history(board_code: str):
    import pandas as pd

    if not board_code:
        return None
    try:
        payload = retry_call(lambda: eastmoney_json(
            "https://7.push2his.eastmoney.com/api/qt/stock/kline/get",
            {
                "secid": f"90.{board_code}",
                "fields1": "f1,f2,f3,f4,f5,f6",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
                "klt": "101",
                "fqt": "0",
                "beg": "19700101",
                "end": "20500101",
                "smplmt": "10000",
                "lmt": "1000000",
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


def _load_constituents(board_code: str):
    import pandas as pd

    if not board_code:
        return None
    try:
        payload = retry_call(lambda: eastmoney_json(
            "https://29.push2.eastmoney.com/api/qt/clist/get",
            {
                "pn": "1",
                "pz": "100",
                "po": "1",
                "np": "1",
                "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                "fltt": "2",
                "invt": "2",
                "fid": "f3",
                "fs": f"b:{board_code} f:!50",
                "fields": (
                    "f2,f3,f4,f5,f6,f7,f8,f9,f12,f14,f15,f16,f17,f18,"
                    "f20,f21,f23,f24,f25,f62,f115,f152"
                ),
            },
        ))
    except Exception:
        return None

    diff = (payload.get("data") or {}).get("diff") or []
    if not diff:
        return None
    return pd.DataFrame(diff)


def _parse_board_spot_row(row) -> dict:
    up_count = safe_int(row.get("f104"))
    down_count = safe_int(row.get("f105"))
    total = sum(x for x in (up_count, down_count) if x is not None)
    return {
        "current_level": safe_float(row.get("f2"), 3),
        "change_pct": safe_float(row.get("f3")),
        "turnover_rate": safe_float(row.get("f8")),
        "up_count": up_count,
        "down_count": down_count,
        "flat_count": None,
        "positive_ratio": round(up_count / total, 3) if total and up_count is not None else None,
        "leader_name": str(row.get("f128") or ""),
        "leader_change_pct": safe_float(row.get("f136")),
    }


def _parse_board_history(df) -> dict:
    import pandas as pd

    date_col = _pick_column(df, ("日期", "date"))
    close_col = _pick_column(df, ("收盘", "close", "最新价"))
    if date_col is None or close_col is None:
        return {}

    frame = df.copy()
    frame[date_col] = pd.to_datetime(frame[date_col], errors="coerce")
    frame = frame.dropna(subset=[date_col]).sort_values(date_col).reset_index(drop=True)
    close = pd.to_numeric(frame[close_col], errors="coerce")
    frame = frame[close.notna()].reset_index(drop=True)
    close = pd.to_numeric(frame[close_col], errors="coerce")
    if frame.empty:
        return {}

    ma20 = close.rolling(20).mean().iloc[-1] if len(close) >= 20 else None
    ma60 = close.rolling(60).mean().iloc[-1] if len(close) >= 60 else None

    return {
        "history_last_date": frame.iloc[-1][date_col].strftime("%Y-%m-%d"),
        "return_5d": _window_return(close, 5),
        "return_20d": _window_return(close, 20),
        "return_60d": _window_return(close, 60),
        "ma20": safe_float(ma20, 3),
        "ma60": safe_float(ma60, 3),
        "price_vs_ma20_pct": pct_change(close.iloc[-1], ma20),
        "price_vs_ma60_pct": pct_change(close.iloc[-1], ma60),
    }


def _parse_constituents(df) -> dict:
    import pandas as pd

    change_col = _pick_column(df, ("涨跌幅", "f3"))
    pe_col = _pick_column(df, ("市盈率-动态", "市盈率", "f115"))
    market_cap_col = _pick_column(df, ("总市值", "f20"))
    name_col = _pick_column(df, ("名称", "f14"))

    change_series = pd.to_numeric(df[change_col], errors="coerce") if change_col else None
    pe_series = pd.to_numeric(df[pe_col], errors="coerce") if pe_col else None
    market_cap_series = pd.to_numeric(df[market_cap_col], errors="coerce") if market_cap_col else None

    positive_ratio = None
    if change_series is not None:
        valid = change_series.dropna()
        if len(valid) > 0:
            positive_ratio = round(float((valid > 0).mean()), 3)

    leaders = []
    if name_col and change_col:
        sorted_df = df.copy()
        sorted_df[change_col] = pd.to_numeric(sorted_df[change_col], errors="coerce")
        sorted_df = sorted_df.sort_values(change_col, ascending=False)
        for _, row in sorted_df.head(5).iterrows():
            leaders.append({
                "name": str(row.get(name_col, "")),
                "change_pct": safe_float(row.get(change_col)),
                "market_cap": safe_float(row.get(market_cap_col)) if market_cap_col else None,
            })

    return {
        "constituent_count": int(len(df)),
        "positive_ratio": positive_ratio,
        "median_pe": safe_float(pe_series.dropna().median()) if pe_series is not None and len(pe_series.dropna()) > 0 else None,
        "median_market_cap": safe_float(market_cap_series.dropna().median()) if market_cap_series is not None and len(market_cap_series.dropna()) > 0 else None,
        "top_constituents": leaders,
    }


def _pick_column(frame, aliases: tuple[str, ...]) -> str | None:
    for alias in aliases:
        if alias in getattr(frame, "columns", []):
            return alias
    return None


def _window_return(series, window: int) -> float | None:
    if len(series) <= window:
        return None
    return pct_change(series.iloc[-1], series.iloc[-window - 1])


def _board_list_host(board_type: str) -> str:
    if board_type == "concept":
        return "https://79.push2.eastmoney.com/api/qt/clist/get"
    return "https://17.push2.eastmoney.com/api/qt/clist/get"


def _board_fs(board_type: str) -> str:
    if board_type == "concept":
        return "m:90 t:3 f:!50"
    return "m:90 t:2 f:!50"


def _scaled_price(value) -> float | None:
    number = safe_float(value, 4)
    if number is None:
        return None
    return round(number / 100, 3)


def _scaled_pct(value) -> float | None:
    number = safe_float(value, 4)
    if number is None:
        return None
    return round(number / 100, 2)
