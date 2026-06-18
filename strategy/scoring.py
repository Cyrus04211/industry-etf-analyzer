"""
行业 ETF 规则化评分引擎 — 增强版（含宏观顺风和情绪信号）
"""
from __future__ import annotations

from data.utils import clamp


def compute_recommendation(payload: dict) -> dict:
    etf = payload.get("etf", {})
    industry = payload.get("industry", {})
    market = payload.get("market", {})
    macro = payload.get("macro", {})
    sentiment = payload.get("sentiment", {})
    broad = market.get("broad_benchmark", {})

    trend_score = _compute_trend_score(etf)
    rs20 = _diff(etf.get("return_20d"), broad.get("return_20d"))
    rs60 = _diff(etf.get("return_60d"), broad.get("return_60d"))
    relative_strength_score = _compute_relative_strength_score(rs20, rs60)
    breadth_score = _compute_breadth_score(industry)
    flow_score = _compute_flow_score(etf)
    macro_score = _compute_macro_tailwind_score(payload)
    sentiment_score = _compute_sentiment_score(sentiment)
    risk_score = _compute_risk_score(etf, market, macro)

    # 增强权重: 趋势30% + 相对强弱25% + 行业扩散20% + 量能10% + 宏观顺风10% + 情绪5%
    total_score = (
        trend_score * 0.30
        + relative_strength_score * 0.25
        + breadth_score * 0.20
        + flow_score * 0.10
        + macro_score * 0.10
        + sentiment_score * 0.05
    )

    # 风险调整
    if risk_score < 35:
        total_score -= 10
    elif risk_score < 50:
        total_score -= 4
    else:
        total_score += min((risk_score - 50) * 0.15, 5)
    total_score = round(clamp(total_score, 0, 100), 1)

    rating = _rating_from_score(total_score)
    action = _action_from_rating(rating)
    position_size = _position_size(total_score, risk_score)
    entry_trigger = _entry_trigger(etf, rating)
    exit_trigger = _exit_trigger(etf)

    reasons = _build_reasons(etf, industry, rs20, market, macro)
    missing_data = _missing_fields(etf, industry, broad, macro, sentiment)
    confidence = _confidence_level(missing_data)

    return {
        "trend_score": trend_score,
        "relative_strength_score": relative_strength_score,
        "breadth_score": breadth_score,
        "flow_score": flow_score,
        "macro_tailwind_score": macro_score,
        "sentiment_score": sentiment_score,
        "risk_score": risk_score,
        "total_score": total_score,
        "relative_strength_20d": rs20,
        "relative_strength_60d": rs60,
        "rating": rating,
        "action": action,
        "position_size": position_size,
        "entry_trigger": entry_trigger,
        "exit_trigger": exit_trigger,
        "holding_period": "5-15个交易日" if total_score >= 60 else "等待下一轮行业轮动",
        "confidence": confidence,
        "reasons": reasons,
        "missing_data": missing_data,
    }


def rank_analyses(analyses: list[dict]) -> list[dict]:
    ranked = sorted(
        analyses,
        key=lambda item: item.get("recommendation", {}).get("total_score", -1),
        reverse=True,
    )
    for index, item in enumerate(ranked, start=1):
        item["rank"] = index
    return ranked


def _compute_trend_score(etf: dict) -> float:
    price = etf.get("current_price")
    ma20 = etf.get("ma20")
    ma60 = etf.get("ma60")
    ma120 = etf.get("ma120")
    ret20 = etf.get("return_20d")
    ret60 = etf.get("return_60d")

    score = 50.0
    score += 12 if _gt(price, ma20) else -12 if ma20 is not None and price is not None else 0
    score += 12 if _gt(price, ma60) else -12 if ma60 is not None and price is not None else 0
    score += 8 if _gt(ma20, ma60) else -8 if ma20 is not None and ma60 is not None else 0
    score += 8 if _gt(ma60, ma120) else -8 if ma60 is not None and ma120 is not None else 0
    if ret20 is not None:
        score += clamp(ret20, -10, 15) * 1.2
    if ret60 is not None:
        score += clamp(ret60, -15, 20) * 0.8
    return round(clamp(score, 0, 100), 1)


def _compute_relative_strength_score(rs20: float | None, rs60: float | None) -> float:
    score = 50.0
    if rs20 is not None:
        score += clamp(rs20, -10, 15) * 2.0
    if rs60 is not None:
        score += clamp(rs60, -15, 20) * 1.2
    return round(clamp(score, 0, 100), 1)


def _compute_breadth_score(industry: dict) -> float:
    ratio = industry.get("positive_ratio")
    change_pct = industry.get("change_pct")
    ret20 = industry.get("return_20d")

    score = 50.0
    if ratio is not None:
        score += (ratio - 0.5) * 80
    if change_pct is not None:
        score += clamp(change_pct, -3, 3) * 8
    if ret20 is not None:
        score += clamp(ret20, -10, 12) * 1.5
    return round(clamp(score, 0, 100), 1)


def _compute_flow_score(etf: dict) -> float:
    volume_ratio = etf.get("volume_ratio_20d")
    amount_ratio = etf.get("amount_ratio_20d")
    turnover_rate = etf.get("turnover_rate")

    score = 50.0
    if volume_ratio is not None:
        score += clamp((volume_ratio - 1.0) * 28, -18, 22)
    if amount_ratio is not None:
        score += clamp((amount_ratio - 1.0) * 24, -16, 20)
    if turnover_rate is not None:
        score += clamp(turnover_rate - 1.2, -5, 8)
    return round(clamp(score, 0, 100), 1)


def _compute_macro_tailwind_score(payload: dict) -> float:
    """
    基于宏观环境判断该行业的顺风/逆风程度。
    核心逻辑:
    - 宏观 expansion + 该行业为周期性/成长型 -> 顺风
    - 宏观 contraction + 该行业为防御型 -> 相对顺风
    - 风格与该行业匹配 -> 加分
    """
    macro = payload.get("macro", {})
    theme = payload.get("theme", "")
    macro_regime = macro.get("macro_regime", {}) if isinstance(macro, dict) else {}
    style = macro.get("style_rotation", {}) if isinstance(macro, dict) else {}

    regime = macro_regime.get("regime", "neutral")
    signals = macro_regime.get("signals", {})
    style_20d = style.get("style_20d", "")

    score = 50.0

    # 宏观 regime 调整
    if regime == "expansion":
        # 扩张期: 周期、成长行业受益
        if theme in ("科技成长", "新能源", "资源", "高端制造"):
            score += 20
        elif theme in ("消费", "金融"):
            score += 10
        elif theme in ("医药",):
            score += 5
        else:
            score += 8
    elif regime == "contraction":
        # 收缩期: 防御、消费、医药相对受益
        if theme in ("金融防御", "消费", "医药"):
            score += 15
        elif theme in ("资源",):
            score -= 5
        elif theme in ("科技成长", "新能源"):
            score -= 10
        else:
            score -= 3

    # PMI 信号
    pmi_signal = signals.get("pmi_signal", "")
    if pmi_signal == "扩张":
        if theme in ("科技成长", "新能源", "资源"):
            score += 8
    elif pmi_signal == "收缩":
        if theme in ("科技成长", "新能源"):
            score -= 5

    # 流动性信号
    liquidity = signals.get("liquidity", "")
    if liquidity == "宽松":
        score += 8  # 流动性宽裕整体利好权益
    elif liquidity == "偏紧":
        score -= 8

    # 风格匹配
    if style_20d == "成长占优" and theme in ("科技成长", "新能源"):
        score += 10
    elif style_20d == "价值占优" and theme in ("金融", "金融防御", "消费", "资源"):
        score += 10

    return round(clamp(score, 0, 100), 1)


def _compute_sentiment_score(sentiment: dict) -> float:
    """
    基于市场情绪和资金流信号评分。
    """
    if not isinstance(sentiment, dict):
        return 50.0

    composite = sentiment.get("composite_signal", {})
    nb = sentiment.get("northbound", {})
    breadth = sentiment.get("market_breadth", {})

    score = 50.0

    # 综合情绪
    overall = composite.get("overall", "")
    if overall == "偏乐观":
        score += 12
    elif overall == "偏谨慎":
        score -= 12

    # 北向资金
    if isinstance(nb, dict):
        net_flow = nb.get("net_flow_yi")
        if net_flow is not None:
            if net_flow > 50:
                score += 15
            elif net_flow > 0:
                score += 8
            elif net_flow < -50:
                score -= 15
            elif net_flow < 0:
                score -= 8

        net_5d = nb.get("net_flow_5d_yi")
        if net_5d is not None:
            if net_5d > 100:
                score += 8
            elif net_5d < -100:
                score -= 8

    # 市场宽度
    if isinstance(breadth, dict):
        up_ratio = breadth.get("up_ratio")
        if up_ratio is not None:
            score += (up_ratio - 0.5) * 40

    return round(clamp(score, 0, 100), 1)


def _compute_risk_score(etf: dict, market: dict, macro: dict = None) -> float:
    score = 70.0
    vol20 = etf.get("volatility_20d")
    drawdown = etf.get("drawdown_from_52w_high_pct")
    price = etf.get("current_price")
    ma20 = etf.get("ma20")

    if vol20 is not None:
        score -= max(vol20 - 22, 0) * 1.3
    if drawdown is not None:
        drawdown_abs = abs(min(drawdown, 0))
        score -= max(drawdown_abs - 18, 0) * 0.8
    if _lt(price, ma20):
        score -= 8
    if market.get("regime") == "risk_off":
        score -= 5

    # 新增: 宏观逆风惩罚
    if isinstance(macro, dict):
        macro_regime = macro.get("macro_regime", {})
        if isinstance(macro_regime, dict) and macro_regime.get("regime") == "contraction":
            score -= 5
        signals = macro_regime.get("signals", {}) if isinstance(macro_regime, dict) else {}
        if signals.get("liquidity") == "偏紧":
            score -= 5

    return round(clamp(score, 0, 100), 1)


def _rating_from_score(score: float) -> str:
    if score >= 75:
        return "积极关注"
    if score >= 60:
        return "偏多"
    if score >= 45:
        return "中性观察"
    return "暂避"


def _action_from_rating(rating: str) -> str:
    mapping = {
        "积极关注": "优先跟踪，允许分批试仓",
        "偏多": "纳入候选，等待更好的执行位置",
        "中性观察": "先观察，不追高",
        "暂避": "放弃当下交易，等待信号重建",
    }
    return mapping[rating]


def _position_size(total_score: float, risk_score: float) -> str:
    if total_score >= 75 and risk_score >= 55:
        return "高"
    if total_score >= 60 and risk_score >= 45:
        return "中"
    if total_score >= 45:
        return "低"
    return "零"


def _entry_trigger(etf: dict, rating: str) -> str:
    price = etf.get("current_price")
    ma20 = etf.get("ma20")
    volume_ratio = etf.get("volume_ratio_20d")
    if rating in ("积极关注", "偏多"):
        if _gt(price, ma20) and volume_ratio is not None and volume_ratio >= 1.1:
            return "回踩 10 日线或 20 日线不破时分批跟踪。"
        if _gt(price, ma20):
            return "等待放量突破近 20 日高点后再跟踪。"
    return "等待重新站回 20 日线并伴随量能回升。"


def _exit_trigger(etf: dict) -> str:
    ma20 = etf.get("ma20")
    if ma20 is not None:
        return f"若收盘连续 2 日跌破 20 日线 {ma20:.3f} 附近，则降低仓位。"
    return "若相对强弱转负且量能同步萎缩，则停止跟踪。"


def _build_reasons(
    etf: dict,
    industry: dict,
    rs20: float | None,
    market: dict,
    macro: dict = None,
) -> list[str]:
    reasons = []
    if _gt(etf.get("current_price"), etf.get("ma20")) and _gt(etf.get("current_price"), etf.get("ma60")):
        reasons.append("ETF 价格位于 20/60 日均线之上，趋势结构偏正向。")
    if rs20 is not None and rs20 > 0:
        reasons.append("近 20 日跑赢沪深 300，说明相对强弱占优。")
    if industry.get("positive_ratio") is not None and industry["positive_ratio"] >= 0.6:
        reasons.append("所属行业上涨家数占比偏高，板块内部扩散较充分。")
    if etf.get("volume_ratio_20d") is not None and etf["volume_ratio_20d"] >= 1.2:
        reasons.append("成交量高于 20 日均值，短线关注度在抬升。")
    if market.get("regime") == "risk_off":
        reasons.append("当前市场整体偏弱，执行上应更保守。")

    # 新增: 宏观和情绪信号
    if isinstance(macro, dict):
        macro_regime = macro.get("macro_regime", {})
        if isinstance(macro_regime, dict):
            regime = macro_regime.get("regime", "")
            if regime == "expansion":
                reasons.append("宏观环境偏扩张，对风险资产友好。")
            elif regime == "contraction":
                reasons.append("宏观环境偏收缩，建议优先考虑防御性行业。")

    if not reasons:
        reasons.append("可用信号有限，优先等待趋势和相对强弱进一步确认。")
    return reasons


def _missing_fields(
    etf: dict,
    industry: dict,
    broad: dict,
    macro: dict = None,
    sentiment: dict = None,
) -> list[str]:
    missing = []
    checks = {
        "etf.current_price": etf.get("current_price"),
        "etf.return_20d": etf.get("return_20d"),
        "etf.ma20": etf.get("ma20"),
        "industry.positive_ratio": industry.get("positive_ratio"),
        "broad.return_20d": broad.get("return_20d"),
    }
    # 新增: 宏观和情绪数据缺口（注意这些为加分项，不影响核心可用性）
    if isinstance(macro, dict):
        macro_regime = macro.get("macro_regime", {})
        if isinstance(macro_regime, dict) and not macro_regime.get("regime"):
            missing.append("macro.regime")
    if isinstance(sentiment, dict):
        composite = sentiment.get("composite_signal", {})
        if isinstance(composite, dict) and not composite.get("overall"):
            missing.append("sentiment.composite")

    for key, value in checks.items():
        if value is None:
            missing.append(key)
    return missing


def _confidence_level(missing_data: list[str]) -> str:
    if len(missing_data) <= 1:
        return "高"
    if len(missing_data) <= 3:
        return "中"
    return "低"


def _diff(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return round(left - right, 1)


def _gt(left: float | None, right: float | None) -> bool:
    return left is not None and right is not None and left > right


def _lt(left: float | None, right: float | None) -> bool:
    return left is not None and right is not None and left < right
