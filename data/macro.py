"""
宏观经济与风格轮动背景 — 为行业ETF轮动提供宏观环境判断

数据来源:
- 中国宏观: AKShare (PMI, CPI, M2, Shibor)
- 美国宏观: FRED (可选, 需 FRED_API_KEY)
- 风格轮动: 从 market.py 的 benchmark 数据推导成长/价值/大小盘风格
"""
from __future__ import annotations

import concurrent.futures

from data.utils import retry_call, safe_float


def get_macro_context(market_style: dict | None = None) -> dict:
    """
    获取宏观经济背景快照。
    market_style: 可选，来自 market.py 的 growth_vs_value 风格数据
    """
    result: dict = {
        "source": "AKShare 宏观经济数据",
        "cn_macro": {},
        "style_rotation": {},
    }

    # 并行拉取中国宏观数据
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(_fetch_pmi): "pmi",
            executor.submit(_fetch_cpi): "cpi",
            executor.submit(_fetch_money_supply): "money_supply",
            executor.submit(_fetch_shibor): "shibor",
        }
        for future in concurrent.futures.as_completed(futures):
            key = futures[future]
            try:
                data = future.result(timeout=20)
                if data:
                    result["cn_macro"][key] = data
            except Exception:
                pass

    # 风格轮动信号
    if market_style:
        result["style_rotation"] = _compute_style_signals(market_style)
    else:
        result["style_rotation"] = {"note": "风格数据未提供，无法计算风格轮动信号"}

    # 宏观环境综合判断
    result["macro_regime"] = _classify_macro_regime(result.get("cn_macro", {}))
    result["macro_summary"] = _build_macro_summary(result)

    return result


def _fetch_pmi() -> dict | None:
    """获取最新 PMI 数据"""
    try:
        import akshare as ak

        df = retry_call(lambda: ak.macro_china_pmi())
        if df.empty:
            return None

        latest = df.sort_values("月份").iloc[-1]
        return {
            "source": "AKShare macro_china_pmi",
            "month": str(latest.get("月份", "")),
            "manufacturing_pmi": safe_float(latest.get("制造业-指数")),
            "non_manufacturing_pmi": safe_float(latest.get("非制造业-指数")),
        }
    except Exception:
        return None


def _fetch_cpi() -> dict | None:
    """获取最新 CPI 数据"""
    try:
        import akshare as ak

        df = retry_call(lambda: ak.macro_china_cpi_monthly())
        if df.empty:
            return None

        latest = df.iloc[-1]
        return {
            "source": "AKShare macro_china_cpi_monthly",
            "date": str(latest.get("日期", "")),
            "value": safe_float(latest.get("今值")),
            "forecast": safe_float(latest.get("预测值")),
            "previous": safe_float(latest.get("前值")),
        }
    except Exception:
        return None


def _fetch_money_supply() -> dict | None:
    """获取最新货币供应量数据"""
    try:
        import akshare as ak

        df = retry_call(lambda: ak.macro_china_money_supply())
        if df.empty:
            return None

        latest = df.sort_values("月份").iloc[-1]
        return {
            "source": "AKShare macro_china_money_supply",
            "month": str(latest.get("月份", "")),
            "m2_yoy": safe_float(latest.get("货币和准货币(M2)-同比增长")),
            "m1_yoy": safe_float(latest.get("货币(M1)-同比增长")),
        }
    except Exception:
        return None


def _fetch_shibor() -> dict | None:
    """获取最新 Shibor 利率"""
    try:
        import akshare as ak

        df = retry_call(
            lambda: ak.rate_interbank(
                market="上海银行间同业拆放利率", symbol="Shibor"
            )
        )
        if df.empty:
            return None

        latest = df.iloc[-1]
        return {
            "source": "AKShare rate_interbank (Shibor)",
            "date": str(latest.iloc[0]) if len(latest) > 0 else "",
            "overnight": safe_float(latest.iloc[1]) if len(latest) > 1 else None,
            "week_1": safe_float(latest.iloc[2]) if len(latest) > 2 else None,
            "month_1": safe_float(latest.iloc[4]) if len(latest) > 4 else None,
        }
    except Exception:
        return None


def _compute_style_signals(market_style: dict) -> dict:
    """
    基于 market.py 提供的成长vs价值差值，判断当前风格偏好。
    market_style 来自 market.py get_market_context() 的 growth_vs_value 字段
    """
    spread_20d = market_style.get("spread_20d")
    spread_60d = market_style.get("spread_60d")

    signals = {
        "source": "基于沪深300ETF / 创业板ETF / 上证50ETF 历史收益差值计算",
    }

    if spread_20d is not None:
        signals["growth_vs_value_spread_20d"] = spread_20d
        if spread_20d > 5:
            signals["style_20d"] = "成长占优"
        elif spread_20d < -5:
            signals["style_20d"] = "价值占优"
        else:
            signals["style_20d"] = "风格中性"

    if spread_60d is not None:
        signals["growth_vs_value_spread_60d"] = spread_60d
        if spread_60d > 8:
            signals["style_60d"] = "成长趋势"
        elif spread_60d < -8:
            signals["style_60d"] = "价值趋势"
        else:
            signals["style_60d"] = "无明显趋势"

    return signals


def _classify_macro_regime(cn_macro: dict) -> dict:
    """
    根据宏观数据判断当前环境：
    - expansion: PMI > 50，M2宽松，适合周期/成长
    - contraction: PMI < 50，偏防御，适合消费/公用事业
    - neutral: 信号混合
    """
    pmi_data = cn_macro.get("pmi", {})
    money_data = cn_macro.get("money_supply", {})
    shibor_data = cn_macro.get("shibor", {})

    signals = {}
    regime = "neutral"

    # PMI 判断
    mfg_pmi = pmi_data.get("manufacturing_pmi") if isinstance(pmi_data, dict) else None
    if mfg_pmi is not None:
        if mfg_pmi > 50:
            signals["pmi_signal"] = "扩张"
        elif mfg_pmi < 50:
            signals["pmi_signal"] = "收缩"
        else:
            signals["pmi_signal"] = "临界"

    # M2 判断
    m2_yoy = money_data.get("m2_yoy") if isinstance(money_data, dict) else None
    if m2_yoy is not None:
        if m2_yoy > 10:
            signals["liquidity"] = "宽松"
        elif m2_yoy < 8:
            signals["liquidity"] = "偏紧"
        else:
            signals["liquidity"] = "中性"

    # Shibor 判断
    overnight = shibor_data.get("overnight") if isinstance(shibor_data, dict) else None
    if overnight is not None:
        if overnight < 1.5:
            signals["interbank"] = "充裕"
        elif overnight > 2.5:
            signals["interbank"] = "偏紧"
        else:
            signals["interbank"] = "正常"

    # 综合 regime
    expansion_count = sum(
        1 for v in signals.values() if v in ("扩张", "宽松", "充裕")
    )
    contraction_count = sum(
        1 for v in signals.values() if v in ("收缩", "偏紧")
    )

    if expansion_count >= 2:
        regime = "expansion"
    elif contraction_count >= 2:
        regime = "contraction"

    return {
        "regime": regime,
        "signals": signals,
        "regime_label": {
            "expansion": "宏观偏扩张 — 周期性行业和成长风格通常受益",
            "contraction": "宏观偏收缩 — 防御性行业和低波动标的通常更稳健",
            "neutral": "宏观信号中性 — 行业轮动更依赖结构性因素",
        }.get(regime, ""),
    }


def _build_macro_summary(macro_data: dict) -> str:
    """生成宏观环境一句话摘要"""
    cn = macro_data.get("cn_macro", {})
    regime = macro_data.get("macro_regime", {})

    parts = []

    pmi = cn.get("pmi", {})
    if isinstance(pmi, dict) and pmi.get("manufacturing_pmi") is not None:
        parts.append(f"制造业PMI {pmi['manufacturing_pmi']} [{pmi.get('month', '')}]")

    money = cn.get("money_supply", {})
    if isinstance(money, dict) and money.get("m2_yoy") is not None:
        parts.append(f"M2同比 {money['m2_yoy']}% [{money.get('month', '')}]")

    style = macro_data.get("style_rotation", {})
    if isinstance(style, dict) and style.get("style_20d"):
        parts.append(f"风格: {style['style_20d']}")

    regime_label = regime.get("regime_label", "") if isinstance(regime, dict) else ""
    if regime_label:
        parts.append(regime_label)

    if not parts:
        return "宏观数据不可用，无法判断当前宏观环境"

    return "；".join(parts)
