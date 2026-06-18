"""
市场快讯 — 增强版（含新鲜度过滤和多源支持）
"""
from __future__ import annotations

from config import ETF_NEWS_MAX_DAYS, ETF_NEWS_MAX_ITEMS
from data.freshness import (
    NARRATIVE_MAX_AGE_DAYS,
    filter_items_by_freshness,
    freshness_meta,
    is_fresh,
)
from data.utils import parse_any_datetime, recent_cutoff, retry_call


def get_market_briefs(keywords: list[str] | None = None) -> dict:
    """获取市场快讯，经新鲜度过滤"""
    raw_items = _fetch_raw_briefs(keywords)
    fresh_items, meta = filter_items_by_freshness(
        raw_items,
        ("published", "date"),
        max_age_days=NARRATIVE_MAX_AGE_DAYS,
    )

    result = {
        "items": fresh_items[:ETF_NEWS_MAX_ITEMS],
        "freshness": freshness_meta(
            fresh_count=len(fresh_items),
            stale_dropped=meta["stale_dropped"],
            unknown_dropped=meta["unknown_date_dropped"],
            max_age_days=NARRATIVE_MAX_AGE_DAYS,
        ),
    }
    if not fresh_items:
        result["note"] = (
            f"近{NARRATIVE_MAX_AGE_DAYS}日内无相关快讯"
            f"（早于 {meta['cutoff_date']} 的条目已丢弃）"
        )
    return result


def _fetch_raw_briefs(keywords: list[str] | None = None) -> list[dict]:
    """从 AKShare 获取原始全球快讯"""
    try:
        import akshare as ak

        df = retry_call(lambda: ak.stock_info_global_em())
    except Exception:
        return []

    if getattr(df, "empty", True):
        return []

    items = []
    keyword_list = [item for item in (keywords or []) if item]
    time_col = _pick_column(df, ("发布时间", "时间", "日期"))
    text_col = _pick_column(df, ("内容", "标题", "摘要"))

    for _, row in df.iterrows():
        published_dt = parse_any_datetime(row.get(time_col) if time_col else None)
        published = published_dt.strftime("%Y-%m-%d %H:%M") if published_dt else ""
        title = str(row.get(text_col, ""))[:180] if text_col else str(row.iloc[0])[:180]

        # 关键词过滤
        if keyword_list and not any(keyword in title for keyword in keyword_list):
            continue

        items.append(
            {
                "published": published,
                "date": published[:10] if published else "",
                "title": title,
                "source": "东方财富全球快讯",
            }
        )

    return items


def _pick_column(frame, aliases: tuple[str, ...]) -> str | None:
    for alias in aliases:
        if alias in getattr(frame, "columns", []):
            return alias
    return None
