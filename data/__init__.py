"""
行业 ETF 数据层统一入口 — 增强版（含宏观、情绪、资金流维度）
"""
from __future__ import annotations

import concurrent.futures


def analyze_universe(verbose: bool = True) -> dict:
    from data.industry import fetch_board_panel
    from data.market import get_market_context
    from data.macro import get_macro_context
    from data.sentiment import get_sentiment_signals
    from data.universe import default_universe
    from strategy.scoring import rank_analyses

    watchlist = default_universe()
    market = get_market_context()
    board_panels = {
        "industry": fetch_board_panel("industry"),
        "concept": fetch_board_panel("concept"),
    }

    # 并行拉取宏观和情绪数据（与行业分析无关，可提前拉取）
    macro = {}
    sentiment = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        macro_future = executor.submit(
            lambda: get_macro_context(market.get("growth_vs_value", {}))
        )
        sentiment_future = executor.submit(get_sentiment_signals)
        try:
            macro = macro_future.result(timeout=30)
        except Exception:
            macro = {"error": "宏观数据拉取失败"}
        try:
            sentiment = sentiment_future.result(timeout=30)
        except Exception:
            sentiment = {"error": "情绪数据拉取失败"}

    if verbose:
        print(f"[INFO] 宏观环境: {macro.get('macro_regime', {}).get('regime', '未知')}")
        print(f"[INFO] 市场情绪: {sentiment.get('composite_signal', {}).get('overall', '未知')}")
        print(f"[INFO] 开始扫描 {len(watchlist)} 只行业 ETF")

    analyses = []
    max_workers = min(6, len(watchlist)) or 1
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                _analyze_entry, entry, market, macro, sentiment, board_panels, True
            ): entry
            for entry in watchlist
        }
        for future in concurrent.futures.as_completed(futures):
            analyses.append(future.result())

    ranked = rank_analyses(analyses)
    briefs = {"items": []}
    return {
        "market": market,
        "macro": macro,
        "sentiment": sentiment,
        "analyses": analyses,
        "ranked": ranked,
        "briefs": briefs,
    }


def analyze_symbol(symbol: str, verbose: bool = True) -> dict:
    from data.industry import fetch_board_panel
    from data.market import get_market_context
    from data.macro import get_macro_context
    from data.sentiment import get_sentiment_signals
    from data.universe import coerce_universe_entry

    entry = coerce_universe_entry(symbol)
    market = get_market_context()

    board_panels = {
        entry.get("board_type", "industry"): fetch_board_panel(
            entry.get("board_type", "industry")
        ),
    }

    # 并行拉取宏观和情绪
    macro = {}
    sentiment = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        macro_future = executor.submit(
            lambda: get_macro_context(market.get("growth_vs_value", {}))
        )
        sentiment_future = executor.submit(get_sentiment_signals)
        try:
            macro = macro_future.result(timeout=30)
        except Exception:
            macro = {"error": "宏观数据拉取失败"}
        try:
            sentiment = sentiment_future.result(timeout=30)
        except Exception:
            sentiment = {"error": "情绪数据拉取失败"}

    if verbose:
        print(f"[INFO] 开始分析 {entry['name']} ({entry['symbol']})")
        print(f"[INFO] 宏观环境: {macro.get('macro_regime', {}).get('regime', '未知')}")

    return _analyze_entry(entry, market, macro, sentiment, board_panels, True)


def _analyze_entry(
    entry: dict,
    market: dict,
    macro: dict,
    sentiment: dict,
    board_panels: dict,
    include_news: bool,
) -> dict:
    from data.industry import get_industry_profile
    from data.news import get_market_briefs
    from data.price import get_etf_price_profile
    from strategy.scoring import compute_recommendation

    etf = get_etf_price_profile(entry["symbol"], entry["name"])
    board_type = entry.get("board_type", "industry")
    relevant_panel = board_panels.get(board_type)
    industry = get_industry_profile(
        entry.get("board_name", ""),
        board_df=relevant_panel,
        board_code=entry.get("board_code", ""),
        board_type=board_type,
    )

    # 新闻：带关键词过滤和新鲜度
    news_keywords = [entry.get("board_name", ""), entry.get("name", "")]
    news = (
        get_market_briefs(news_keywords)
        if include_news
        else {"items": [], "freshness": {}}
    )

    payload = {
        "symbol": entry["symbol"],
        "name": entry["name"],
        "theme": entry.get("theme", ""),
        "board_name": entry.get("board_name", ""),
        "board_code": entry.get("board_code", ""),
        "board_type": entry.get("board_type", "industry"),
        "etf": etf,
        "industry": industry,
        "market": market,
        "macro": macro,
        "sentiment": sentiment,
        "news": news,
    }
    payload["recommendation"] = compute_recommendation(payload)
    return payload
