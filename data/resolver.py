"""
LLM Prompt 上下文构建 — 将原始数据整理为 LLM 可读的结构化文本
"""
from __future__ import annotations

import json
from datetime import datetime


def build_single_etf_context(analysis: dict) -> str:
    """构建单只 ETF 的完整分析上下文，供 LLM 深度分析使用"""
    etf = analysis.get("etf", {})
    industry = analysis.get("industry", {})
    market = analysis.get("market", {})
    macro = analysis.get("macro", {})
    sentiment = analysis.get("sentiment", {})
    news = analysis.get("news", {})
    derived = analysis.get("derived", {})

    broad = market.get("broad_benchmark", {})
    macro_regime = macro.get("macro_regime", {}) if isinstance(macro, dict) else {}
    cn_macro = macro.get("cn_macro", {}) if isinstance(macro, dict) else {}
    style = macro.get("style_rotation", {}) if isinstance(macro, dict) else {}
    composite = sentiment.get("composite_signal", {}) if isinstance(sentiment, dict) else {}
    nb = sentiment.get("northbound", {}) if isinstance(sentiment, dict) else {}
    breadth = sentiment.get("market_breadth", {}) if isinstance(sentiment, dict) else {}
    news_items = news.get("items", []) if isinstance(news, dict) else []
    freshness = news.get("freshness", {}) if isinstance(news, dict) else {}

    context = {
        "symbol": analysis.get("symbol"),
        "name": analysis.get("name"),
        "theme": analysis.get("theme"),
        "board_name": analysis.get("board_name"),
        "分析时间": datetime.now().strftime("%Y-%m-%d %H:%M"),

        # ETF 行情 (L1-事实)
        "ETF行情": {
            "最新价": etf.get("current_price"),
            "当日涨跌幅_pct": etf.get("change_pct"),
            "近5日收益_pct": etf.get("return_5d"),
            "近20日收益_pct": etf.get("return_20d"),
            "近60日收益_pct": etf.get("return_60d"),
            "年内收益_pct": etf.get("return_ytd"),
            "20日均线": etf.get("ma20"),
            "60日均线": etf.get("ma60"),
            "120日均线": etf.get("ma120"),
            "价格vs20日线_pct": etf.get("price_vs_ma20_pct"),
            "价格vs60日线_pct": etf.get("price_vs_ma60_pct"),
            "52周最高": etf.get("high_52w"),
            "52周最低": etf.get("low_52w"),
            "52周回撤_pct": etf.get("drawdown_from_52w_high_pct"),
            "20日波动率_年化": etf.get("volatility_20d"),
            "60日波动率_年化": etf.get("volatility_60d"),
            "成交量比_20日": etf.get("volume_ratio_20d"),
            "成交额比_20日": etf.get("amount_ratio_20d"),
            "换手率": etf.get("turnover_rate"),
            "来源": etf.get("source", ""),
            "数据日期": etf.get("last_date", ""),
        },

        # 相对强弱 (L2-计算)
        "相对强弱": {
            "相对沪深300_20日_pct": derived.get("relative_strength_20d"),
            "相对沪深300_60日_pct": derived.get("relative_strength_60d"),
            "沪深300_20日收益_pct": broad.get("return_20d"),
            "沪深300_60日收益_pct": broad.get("return_60d"),
        },

        # 行业板块 (L1-事实)
        "行业板块": {
            "板块名称": industry.get("board_name"),
            "板块代码": industry.get("board_code"),
            "板块类型": industry.get("board_type"),
            "板块当日涨跌幅_pct": industry.get("change_pct"),
            "板块近20日涨跌_pct": industry.get("return_20d"),
            "板块近60日涨跌_pct": industry.get("return_60d"),
            "上涨家数": industry.get("up_count"),
            "下跌家数": industry.get("down_count"),
            "上涨占比": industry.get("positive_ratio"),
            "领涨股": industry.get("leader_name"),
            "领涨股涨幅_pct": industry.get("leader_change_pct"),
            "板块PE中位数": industry.get("median_pe"),
            "来源": industry.get("source", ""),
        },

        # 市场环境 (L1/L2)
        "市场环境": {
            "市场状态": market.get("regime"),
            "状态说明": market.get("summary"),
            "成长vs价值_20日差值_pct": market.get("growth_vs_value", {}).get("spread_20d"),
            "成长vs价值_60日差值_pct": market.get("growth_vs_value", {}).get("spread_60d"),
        },

        # 宏观背景 (L1-事实)
        "宏观背景": {
            "宏观环境": macro_regime.get("regime"),
            "环境说明": macro_regime.get("regime_label"),
            "宏观摘要": macro.get("macro_summary", ""),
            "PMI_制造业": cn_macro.get("pmi", {}).get("manufacturing_pmi") if isinstance(cn_macro.get("pmi"), dict) else None,
            "PMI_非制造业": cn_macro.get("pmi", {}).get("non_manufacturing_pmi") if isinstance(cn_macro.get("pmi"), dict) else None,
            "PMI_月份": cn_macro.get("pmi", {}).get("month") if isinstance(cn_macro.get("pmi"), dict) else "",
            "M2同比_pct": cn_macro.get("money_supply", {}).get("m2_yoy") if isinstance(cn_macro.get("money_supply"), dict) else None,
            "M1同比_pct": cn_macro.get("money_supply", {}).get("m1_yoy") if isinstance(cn_macro.get("money_supply"), dict) else None,
            "CP近期值": cn_macro.get("cpi", {}).get("value") if isinstance(cn_macro.get("cpi"), dict) else None,
            "Shibor隔夜": cn_macro.get("shibor", {}).get("overnight") if isinstance(cn_macro.get("shibor"), dict) else None,
            "宏观信号": macro_regime.get("signals", {}),
            "风格偏好_20日": style.get("style_20d"),
            "来源": macro.get("source", ""),
        },

        # 情绪与资金流 (L1-事实)
        "情绪资金流": {
            "综合情绪": composite.get("overall"),
            "情绪详情": composite.get("details", []),
            "北向资金_当日净流向_亿元": nb.get("net_flow_yi"),
            "北向资金_5日累计_亿元": nb.get("net_flow_5d_yi"),
            "北向资金_信号": nb.get("signal"),
            "北向资金_日期": nb.get("date"),
            "北向来源": nb.get("source"),
            "全市场上涨占比": breadth.get("up_ratio"),
            "全市场上涨家数": breadth.get("up_count"),
            "全市场下跌家数": breadth.get("down_count"),
            "市场宽度信号": breadth.get("signal"),
            "融资余额_亿元": sentiment.get("margin", {}).get("margin_balance_yi") if isinstance(sentiment.get("margin"), dict) else None,
            "融资信号": sentiment.get("margin", {}).get("signal") if isinstance(sentiment.get("margin"), dict) else None,
        },

        # 相关快讯 (仅近7日)
        "相关快讯": [
            {
                "时间": item.get("published"),
                "标题": item.get("title"),
                "来源": item.get("source"),
            }
            for item in news_items[:8]
        ],
        "快讯时效": {
            "近7日可用": freshness.get("fresh_count", 0),
            "过期丢弃": freshness.get("stale_dropped", 0),
            "截止日期": freshness.get("cutoff_date"),
        },
    }

    return json.dumps(context, ensure_ascii=False, indent=2, default=str)


def build_universe_context(bundle: dict, top_n: int = 12) -> str:
    """
    构建全行业扫描的上下文，供 LLM 排名和分析使用。
    包含所有 ETF 的关键指标 + 宏观/情绪背景。
    """
    market = bundle.get("market", {})
    macro = bundle.get("macro", {})
    sentiment = bundle.get("sentiment", {})
    analyses = bundle.get("analyses", [])

    broad = market.get("broad_benchmark", {})
    macro_regime = macro.get("macro_regime", {}) if isinstance(macro, dict) else {}
    cn_macro = macro.get("cn_macro", {}) if isinstance(macro, dict) else {}
    style = macro.get("style_rotation", {}) if isinstance(macro, dict) else {}
    composite = sentiment.get("composite_signal", {}) if isinstance(sentiment, dict) else {}
    nb = sentiment.get("northbound", {}) if isinstance(sentiment, dict) else {}
    breadth = sentiment.get("market_breadth", {}) if isinstance(sentiment, dict) else {}

    # 按近20日收益排序作为参考（非硬编码评分，仅用于排序呈现）
    sorted_analyses = sorted(
        analyses,
        key=lambda a: a.get("etf", {}).get("return_20d") or -999,
        reverse=True,
    )

    etf_table = []
    for idx, item in enumerate(sorted_analyses[:top_n], 1):
        etf = item.get("etf", {})
        ind = item.get("industry", {})
        d = item.get("derived", {})
        etf_table.append({
            "序号": idx,
            "代码": item.get("symbol"),
            "名称": item.get("name"),
            "主题": item.get("theme"),
            "最新价": etf.get("current_price"),
            "当日涨跌_pct": etf.get("change_pct"),
            "近5日_pct": etf.get("return_5d"),
            "近20日_pct": etf.get("return_20d"),
            "近60日_pct": etf.get("return_60d"),
            "年内_pct": etf.get("return_ytd"),
            "相对沪深300_20日_pct": d.get("relative_strength_20d"),
            "相对沪深300_60日_pct": d.get("relative_strength_60d"),
            "价格vs20日线_pct": etf.get("price_vs_ma20_pct"),
            "20日波动率": etf.get("volatility_20d"),
            "量比_20日": etf.get("volume_ratio_20d"),
            "52周回撤_pct": etf.get("drawdown_from_52w_high_pct"),
            "板块名称": item.get("board_name"),
            "板块涨跌_pct": ind.get("change_pct"),
            "板块上涨占比": ind.get("positive_ratio"),
            "板块领涨股": ind.get("leader_name"),
            "领涨股涨幅_pct": ind.get("leader_change_pct"),
        })

    context = {
        "分析时间": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "扫描ETF数量": len(analyses),

        "宏观环境": {
            "宏观定位": macro_regime.get("regime"),
            "环境说明": macro_regime.get("regime_label"),
            "宏观摘要": macro.get("macro_summary", ""),
            "PMI制造业": cn_macro.get("pmi", {}).get("manufacturing_pmi") if isinstance(cn_macro.get("pmi"), dict) else None,
            "M2同比_pct": cn_macro.get("money_supply", {}).get("m2_yoy") if isinstance(cn_macro.get("money_supply"), dict) else None,
            "风格偏好": style.get("style_20d"),
            "成长vs价值差值": market.get("growth_vs_value", {}).get("spread_20d"),
        },

        "市场环境": {
            "市场状态": market.get("regime"),
            "状态说明": market.get("summary"),
            "沪深300_20日_pct": broad.get("return_20d"),
            "沪深300_60日_pct": broad.get("return_60d"),
        },

        "情绪资金面": {
            "综合情绪": composite.get("overall"),
            "北向当日净流向_亿": nb.get("net_flow_yi"),
            "北向5日累计_亿": nb.get("net_flow_5d_yi"),
            "北向信号": nb.get("signal"),
            "全市场上涨占比": breadth.get("up_ratio"),
        },

        "ETF指标总表": etf_table,
    }

    return json.dumps(context, ensure_ascii=False, indent=2, default=str)
