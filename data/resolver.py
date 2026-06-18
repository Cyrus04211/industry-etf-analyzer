"""
LLM/报告使用的结构化快照 — 增强版（含宏观、情绪、资金流维度）
"""
from __future__ import annotations

import json
from datetime import datetime


def build_analysis_snapshot(analysis: dict) -> dict:
    etf = analysis.get("etf", {})
    industry = analysis.get("industry", {})
    market = analysis.get("market", {})
    recommendation = analysis.get("recommendation", {})
    broad = market.get("broad_benchmark", {})

    return {
        "symbol": analysis.get("symbol"),
        "name": analysis.get("name"),
        "theme": analysis.get("theme"),
        "board_name": analysis.get("board_name"),
        "etf": {
            "current_price": etf.get("current_price"),
            "change_pct": etf.get("change_pct"),
            "return_20d": etf.get("return_20d"),
            "return_60d": etf.get("return_60d"),
            "ma20": etf.get("ma20"),
            "ma60": etf.get("ma60"),
            "volume_ratio_20d": etf.get("volume_ratio_20d"),
            "amount_ratio_20d": etf.get("amount_ratio_20d"),
            "volatility_20d": etf.get("volatility_20d"),
            "drawdown_from_52w_high_pct": etf.get("drawdown_from_52w_high_pct"),
            "source": etf.get("source"),
            "last_date": etf.get("last_date"),
        },
        "industry": {
            "change_pct": industry.get("change_pct"),
            "return_20d": industry.get("return_20d"),
            "return_60d": industry.get("return_60d"),
            "positive_ratio": industry.get("positive_ratio"),
            "up_count": industry.get("up_count"),
            "down_count": industry.get("down_count"),
            "leader_name": industry.get("leader_name"),
            "leader_change_pct": industry.get("leader_change_pct"),
            "median_pe": industry.get("median_pe"),
            "source": industry.get("source"),
        },
        "market": {
            "regime": market.get("regime"),
            "summary": market.get("summary"),
            "broad_benchmark_return_20d": broad.get("return_20d"),
            "broad_benchmark_return_60d": broad.get("return_60d"),
            "growth_vs_value_20d": market.get("growth_vs_value", {}).get("spread_20d"),
        },
        "recommendation": recommendation,
        "news": analysis.get("news", {}).get("items", []),
    }


def build_single_prompt_context(analysis: dict) -> str:
    return json.dumps(build_analysis_snapshot(analysis), ensure_ascii=False, indent=2)


def build_universe_prompt_context(bundle: dict, top_n: int = 5) -> str:
    ranked = bundle.get("ranked", [])[:top_n]
    payload = {
        "market": {
            "regime": bundle.get("market", {}).get("regime"),
            "summary": bundle.get("market", {}).get("summary"),
            "growth_vs_value_20d": bundle.get("market", {}).get("growth_vs_value", {}).get("spread_20d"),
        },
        "top_etfs": [
            {
                "rank": item.get("rank"),
                "symbol": item.get("symbol"),
                "name": item.get("name"),
                "theme": item.get("theme"),
                "rating": item.get("recommendation", {}).get("rating"),
                "total_score": item.get("recommendation", {}).get("total_score"),
                "action": item.get("recommendation", {}).get("action"),
                "return_20d": item.get("etf", {}).get("return_20d"),
                "vs_hs300_20d": item.get("recommendation", {}).get("relative_strength_20d"),
                "industry_positive_ratio": item.get("industry", {}).get("positive_ratio"),
            }
            for item in ranked
        ],
        "market_briefs": bundle.get("briefs", {}).get("items", []),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


# ═════════════════════════════════════════════
# 增强版快照: 包含宏观、情绪、资金流维度
# ═════════════════════════════════════════════

def build_enhanced_snapshot(analysis: dict) -> str:
    """
    构建增强版单ETF分析快照 — 包含宏观、情绪、资金流维度。
    用于 LLM prompt 注入。
    """
    base = build_analysis_snapshot(analysis)

    # 新增: 宏观维度
    macro = analysis.get("macro", {})
    cn_macro = macro.get("cn_macro", {}) if isinstance(macro, dict) else {}
    macro_regime = macro.get("macro_regime", {}) if isinstance(macro, dict) else {}
    style = macro.get("style_rotation", {}) if isinstance(macro, dict) else {}

    base["macro"] = {
        "regime": macro_regime.get("regime", "数据不可用"),
        "regime_label": macro_regime.get("regime_label", ""),
        "signals": macro_regime.get("signals", {}),
        "summary": macro.get("macro_summary", ""),
        "pmi": cn_macro.get("pmi", {}),
        "money_supply": cn_macro.get("money_supply", {}),
        "shibor": cn_macro.get("shibor", {}),
        "style_rotation": {
            "growth_vs_value_20d": style.get("growth_vs_value_spread_20d"),
            "style_20d": style.get("style_20d"),
            "source": style.get("source", ""),
        },
    }

    # 新增: 情绪与资金流维度
    sentiment = analysis.get("sentiment", {})
    if isinstance(sentiment, dict):
        nb = sentiment.get("northbound", {})
        breadth = sentiment.get("market_breadth", {})
        margin = sentiment.get("margin", {})
        composite = sentiment.get("composite_signal", {})

        base["sentiment"] = {
            "overall": composite.get("overall", "数据不可用"),
            "details": composite.get("details", []),
            "northbound": {
                "date": nb.get("date", ""),
                "net_flow_yi": nb.get("net_flow_yi"),
                "net_flow_5d_yi": nb.get("net_flow_5d_yi"),
                "signal": nb.get("signal", ""),
                "source": nb.get("source", ""),
            } if nb else {},
            "market_breadth": {
                "up_ratio": breadth.get("up_ratio"),
                "up_count": breadth.get("up_count"),
                "down_count": breadth.get("down_count"),
                "signal": breadth.get("signal", ""),
                "source": breadth.get("source", ""),
            } if breadth else {},
            "margin": {
                "date": margin.get("date", ""),
                "margin_balance_yi": margin.get("margin_balance_yi"),
                "signal": margin.get("signal", ""),
                "source": margin.get("source", ""),
            } if margin else {},
        }

    # 新增: 新闻新鲜度信息
    news = analysis.get("news", {})
    if isinstance(news, dict):
        freshness = news.get("freshness", {})
        base["news_meta"] = {
            "fresh_count": freshness.get("fresh_count", 0),
            "stale_dropped": freshness.get("stale_dropped", 0),
            "cutoff_date": freshness.get("cutoff_date", ""),
            "policy": f"仅保留近{freshness.get('max_age_days', 7)}日新闻",
        }

    return json.dumps(base, ensure_ascii=False, indent=2, default=str)


def build_universe_snapshot(bundle: dict, top_n: int = 5) -> str:
    """
    构建增强版轮动扫描快照 — 包含宏观和情绪维度。
    """
    market = bundle.get("market", {})
    macro = bundle.get("macro", {})
    sentiment = bundle.get("sentiment", {})
    ranked = bundle.get("ranked", [])[:top_n]

    cn_macro = macro.get("cn_macro", {}) if isinstance(macro, dict) else {}
    macro_regime = macro.get("macro_regime", {}) if isinstance(macro, dict) else {}
    style = macro.get("style_rotation", {}) if isinstance(macro, dict) else {}
    composite = sentiment.get("composite_signal", {}) if isinstance(sentiment, dict) else {}

    payload = {
        "market": {
            "regime": market.get("regime"),
            "summary": market.get("summary"),
            "growth_vs_value_20d": market.get("growth_vs_value", {}).get("spread_20d"),
        },
        "macro": {
            "regime": macro_regime.get("regime", "数据不可用"),
            "summary": macro.get("macro_summary", ""),
            "pmi_manufacturing": cn_macro.get("pmi", {}).get("manufacturing_pmi") if isinstance(cn_macro.get("pmi"), dict) else None,
            "m2_yoy": cn_macro.get("money_supply", {}).get("m2_yoy") if isinstance(cn_macro.get("money_supply"), dict) else None,
            "style_20d": style.get("style_20d", ""),
            "source": "AKShare 宏观经济数据",
        },
        "sentiment": {
            "overall": composite.get("overall", "数据不可用"),
            "details": composite.get("details", []),
            "source": "综合（AKShare / 东方财富）",
        },
        "top_etfs": [
            {
                "rank": item.get("rank"),
                "symbol": item.get("symbol"),
                "name": item.get("name"),
                "theme": item.get("theme"),
                "rating": item.get("recommendation", {}).get("rating"),
                "total_score": item.get("recommendation", {}).get("total_score"),
                "action": item.get("recommendation", {}).get("action"),
                "return_20d": item.get("etf", {}).get("return_20d"),
                "vs_hs300_20d": item.get("recommendation", {}).get("relative_strength_20d"),
                "industry_positive_ratio": item.get("industry", {}).get("positive_ratio"),
                "macro_tailwind_score": item.get("recommendation", {}).get("macro_tailwind_score"),
                "sentiment_score": item.get("recommendation", {}).get("sentiment_score"),
            }
            for item in ranked
        ],
        "market_briefs": bundle.get("briefs", {}).get("items", []),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str)


def facts_summary_for_prompt(analysis: dict) -> str:
    """带来源标注的核心事实摘要，优先注入 LLM prompt"""
    etf = analysis.get("etf", {})
    industry = analysis.get("industry", {})
    market = analysis.get("market", {})
    rec = analysis.get("recommendation", {})
    macro = analysis.get("macro", {})
    sentiment = analysis.get("sentiment", {})
    news = analysis.get("news", {})

    macro_regime = macro.get("macro_regime", {}) if isinstance(macro, dict) else {}
    cn_macro = macro.get("cn_macro", {}) if isinstance(macro, dict) else {}
    composite = sentiment.get("composite_signal", {}) if isinstance(sentiment, dict) else {}
    freshness = news.get("freshness", {}) if isinstance(news, dict) else {}

    lines = [
        "## 已验证核心事实（必须使用，并标注来源）",
        f"- ETF当前价: {etf.get('current_price')} [{etf.get('source') or '来源缺失'}] (数据日期: {etf.get('last_date', '未知')})",
        f"- 当日涨跌幅: {etf.get('change_pct')}% [{etf.get('source') or '来源缺失'}]",
        f"- 近20日/60日收益: {etf.get('return_20d')}% / {etf.get('return_60d')}% [{etf.get('source') or '来源缺失'}]",
        f"- 相对沪深300 (20日): {rec.get('relative_strength_20d')}pct [计算自 Eastmoney ETF + 沪深300ETF 行情]",
        f"- 20日/60日均线: {etf.get('ma20')} / {etf.get('ma60')} [{etf.get('source') or '来源缺失'}]",
        "",
        f"## 行业板块事实",
        f"- 行业板块当日涨跌幅: {industry.get('change_pct')}% [{industry.get('source') or '来源缺失'}]",
        f"- 行业上涨家数占比: {industry.get('positive_ratio')} [{industry.get('source') or '来源缺失'}]",
        f"- 行业领涨股: {industry.get('leader_name')} ({industry.get('leader_change_pct')}%) [{industry.get('source') or '来源缺失'}]",
        "",
        f"## 市场环境",
        f"- 市场状态: {market.get('regime')} | {market.get('summary')}",
        f"- 成长vs价值 (20日差值): {market.get('growth_vs_value', {}).get('spread_20d')}pct",
        "",
        f"## 宏观背景",
        f"- 宏观环境: {macro_regime.get('regime', '数据不可用')}",
        f"- 宏观摘要: {macro.get('macro_summary', '数据不可用')}",
        f"- 风格偏好 (20日): {macro.get('style_rotation', {}).get('style_20d', '数据不可用')}",
        "",
        f"## 情绪与资金面",
        f"- 整体情绪: {composite.get('overall', '数据不可用')}",
        f"- 情绪细节: {', '.join(composite.get('details', [])) or '数据不可用'}",
    ]

    # 北向资金
    nb = sentiment.get("northbound", {}) if isinstance(sentiment, dict) else {}
    if isinstance(nb, dict) and nb.get("net_flow_yi") is not None:
        lines.append(f"- 北向资金净流向: {nb['net_flow_yi']}亿 [{nb.get('source', '')}] (日期: {nb.get('date', '')})")

    # 市场宽度
    breadth = sentiment.get("market_breadth", {}) if isinstance(sentiment, dict) else {}
    if isinstance(breadth, dict) and breadth.get("up_ratio") is not None:
        lines.append(f"- 全市场上涨占比: {breadth['up_ratio']:.0%} [{breadth.get('source', '')}]")

    lines.extend([
        "",
        f"## 新闻快讯时效",
        f"- 近7日相关快讯: {freshness.get('fresh_count', 0)} 条",
        f"- 过期丢弃: {freshness.get('stale_dropped', 0)} 条",
        f"- 截止日期: {freshness.get('cutoff_date', '')}",
        "",
        "## 分析纪律（必须遵守）",
        "1. 每个数值结论必须标注来源（如「Eastmoney ETF quote」「AKShare 宏观数据」）",
        "2. 数据缺失时明确写「数据不可用」，禁止用「可能」「假设」填补关键数字",
        "3. 推断必须基于已给数据，并写明推断逻辑；不得捏造政策、资金流、新闻等未提供的数据",
        "4. 新闻标题只能引用近7日内快照中存在的条目；更早的一律不得引用",
        "5. 若近7日无相关快讯，叙事部分须明确写「近一周无相关消息」",
    ])

    return "\n".join(lines)
