"""
市场情绪与资金流信号 — 为行业ETF轮动提供资金面和情绪维度

数据来源:
- 北向资金: AKShare stock_hsgt_north_net_flow_in_em
- 融资融券: AKShare stock_margin_sz/stock_margin_sh
- 市场宽度: AKShare stock_zh_a_spot_em (全市场涨跌统计)
- ETF份额变动: 东方财富 fund_etf_fund_daily_em
"""
from __future__ import annotations

import concurrent.futures

from data.utils import retry_call, safe_float


def get_sentiment_signals() -> dict:
    """
    获取市场情绪和资金流的综合信号。
    返回结构化的情绪快照。
    """
    result: dict = {
        "source": "综合（AKShare / 东方财富）",
        "northbound": {},
        "margin": {},
        "market_breadth": {},
    }

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(_fetch_northbound_flow): "northbound",
            executor.submit(_fetch_margin_data): "margin",
            executor.submit(_fetch_market_breadth): "breadth",
        }
        for future in concurrent.futures.as_completed(futures):
            key = futures[future]
            try:
                data = future.result(timeout=20)
                if data:
                    result[key] = data
            except Exception:
                pass

    # 综合情绪判断
    result["composite_signal"] = _compute_composite(result)

    return result


def _fetch_northbound_flow() -> dict | None:
    """获取北向资金净流向"""
    try:
        import akshare as ak

        df = retry_call(lambda: ak.stock_hsgt_north_net_flow_in_em(symbol="北上"))
        if df.empty:
            return None

        latest = df.iloc[-1]
        recent5 = df.tail(5) if len(df) >= 5 else df

        net_flow = safe_float(latest.get("value"))
        date_str = str(latest.get("date", ""))

        # 计算5日累计
        net_5d = 0.0
        if "value" in recent5.columns:
            net_5d = sum(
                safe_float(v) or 0.0 for v in recent5["value"]
            )

        signal = "中性"
        if net_flow is not None:
            if net_flow > 50:
                signal = "大幅净流入 — 外资偏乐观"
            elif net_flow > 0:
                signal = "小幅净流入"
            elif net_flow > -50:
                signal = "小幅净流出"
            else:
                signal = "大幅净流出 — 外资偏谨慎"

        return {
            "source": "AKShare stock_hsgt_north_net_flow_in_em",
            "date": date_str,
            "net_flow_yi": net_flow,  # 亿元
            "net_flow_5d_yi": round(net_5d, 2) if net_5d else None,
            "signal": signal,
        }
    except Exception:
        return None


def _fetch_margin_data() -> dict | None:
    """获取融资融券余额变化"""
    try:
        import akshare as ak

        df_sh = retry_call(lambda: ak.stock_margin_detail_sse(date=""))
        if df_sh.empty:
            return None

        # 取最近一条
        latest = df_sh.iloc[-1]
        margin_balance = safe_float(latest.get("融资余额"))
        date_str = str(latest.get("信用交易日期", ""))

        signal = "数据不可用"
        if margin_balance is not None:
            # 粗略判断: 两市融资余额 > 1.5万亿视为活跃
            signal = "融资余额活跃" if margin_balance > 1.5e4 else "融资余额偏低"

        return {
            "source": "AKShare stock_margin_detail_sse",
            "date": date_str,
            "margin_balance_yi": round(margin_balance / 1e8, 2) if margin_balance else None,
            "signal": signal,
        }
    except Exception:
        return None


def _fetch_market_breadth() -> dict | None:
    """获取全市场上涨/下跌家数比（市场宽度）"""
    try:
        import akshare as ak

        df = retry_call(lambda: ak.stock_zh_a_spot_em())
        if df.empty:
            return None

        if "涨跌幅" not in df.columns:
            return None

        import pandas as pd
        change = pd.to_numeric(df["涨跌幅"], errors="coerce").dropna()
        total = len(change)
        up_count = int((change > 0).sum())
        down_count = int((change < 0).sum())
        flat_count = total - up_count - down_count

        up_ratio = round(up_count / total, 3) if total > 0 else None

        signal = "中性"
        if up_ratio is not None:
            if up_ratio > 0.65:
                signal = "普涨 — 市场热情偏高"
            elif up_ratio > 0.50:
                signal = "偏多 — 多数个股上涨"
            elif up_ratio > 0.35:
                signal = "分化 — 涨跌互现，选股/选行业重要"
            else:
                signal = "普跌 — 市场情绪偏弱"

        return {
            "source": "AKShare stock_zh_a_spot_em 实时全市场统计",
            "total_stocks": total,
            "up_count": up_count,
            "down_count": down_count,
            "flat_count": flat_count,
            "up_ratio": up_ratio,
            "signal": signal,
        }
    except Exception:
        return None


def _compute_composite(signals: dict) -> dict:
    """综合各维度信号，给出整体情绪判断"""
    bullish = 0
    bearish = 0
    details = []

    nb = signals.get("northbound", {})
    if isinstance(nb, dict):
        net = nb.get("net_flow_yi")
        if net is not None:
            if net > 30:
                bullish += 1
                details.append(f"北向大幅净流入 ({net:.1f}亿)")
            elif net < -30:
                bearish += 1
                details.append(f"北向大幅净流出 ({net:.1f}亿)")
            else:
                details.append(f"北向资金中性 ({net:.1f}亿)")

    bread = signals.get("market_breadth", {})
    if isinstance(bread, dict):
        ratio = bread.get("up_ratio")
        if ratio is not None:
            if ratio > 0.6:
                bullish += 1
                details.append(f"市场宽度偏多 (上涨占比 {ratio:.0%})")
            elif ratio < 0.4:
                bearish += 1
                details.append(f"市场宽度偏空 (上涨占比 {ratio:.0%})")

    margin = signals.get("margin", {})
    if isinstance(margin, dict) and margin.get("signal") not in (None, "数据不可用"):
        details.append(f"融资: {margin['signal']}")

    if bullish > bearish:
        overall = "偏乐观"
    elif bearish > bullish:
        overall = "偏谨慎"
    else:
        overall = "中性"

    return {
        "overall": overall,
        "bullish_signals": bullish,
        "bearish_signals": bearish,
        "details": details,
    }
