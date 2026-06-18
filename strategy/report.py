"""
Markdown 报告渲染 — 增强版（含宏观、情绪、资金流、数据来源标注）
"""
from __future__ import annotations

from datetime import datetime


def render_single_report(analysis: dict, llm_text: str | None = None) -> str:
    etf = analysis.get("etf", {})
    industry = analysis.get("industry", {})
    market = analysis.get("market", {})
    rec = analysis.get("recommendation", {})
    macro = analysis.get("macro", {})
    sentiment = analysis.get("sentiment", {})
    news = analysis.get("news", {})
    news_items = news.get("items", []) if isinstance(news, dict) else []
    freshness = news.get("freshness", {}) if isinstance(news, dict) else {}

    # 宏观摘要
    macro_regime = macro.get("macro_regime", {}) if isinstance(macro, dict) else {}
    macro_summary = macro.get("macro_summary", "") if isinstance(macro, dict) else ""
    style = macro.get("style_rotation", {}) if isinstance(macro, dict) else {}

    # 情绪摘要
    composite = sentiment.get("composite_signal", {}) if isinstance(sentiment, dict) else {}
    nb = sentiment.get("northbound", {}) if isinstance(sentiment, dict) else {}
    breadth = sentiment.get("market_breadth", {}) if isinstance(sentiment, dict) else {}

    news_block = "\n".join(
        f"- {item.get('published') or '日期缺失'} | {item.get('title')} [{item.get('source')}]"
        for item in news_items[:6]
    ) or "- 近一周未筛到相关快讯"

    # 新闻新鲜度
    freshness_note = ""
    if freshness:
        freshness_note = (
            f"（近{freshness.get('max_age_days', 7)}日内 {freshness.get('fresh_count', 0)} 条，"
            f"丢弃过期 {freshness.get('stale_dropped', 0)} 条）"
        )

    llm_block = f"\n\n## AI 扩展解读\n\n{llm_text}\n" if llm_text else ""

    return f"""# 行业 ETF 深度分析 | {analysis.get('name')} ({analysis.get('symbol')})

**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
**所属主题**: {analysis.get('theme')}
**对应行业板块**: {analysis.get('board_name') or '未映射'}
**投资评级**: {rec.get('rating')}
**综合得分**: {rec.get('total_score')}/100
**执行建议**: {rec.get('action')}
**置信度**: {rec.get('confidence')}

---

## 宏观背景

- 宏观环境: **{macro_regime.get('regime', '数据不可用')}** | {macro_regime.get('regime_label', '')}
- 宏观摘要: {macro_summary or '数据不可用'}
- 风格偏好 (20日): {style.get('style_20d', '数据不可用')} | 成长vs价值差值: {_fmt_delta(style.get('growth_vs_value_spread_20d'))}
- PMI 信号: {macro_regime.get('signals', {}).get('pmi_signal', '数据不可用')}
- 流动性: {macro_regime.get('signals', {}).get('liquidity', '数据不可用')} | 同业拆借: {macro_regime.get('signals', {}).get('interbank', '数据不可用')}
- 宏观数据来源: {macro.get('source', 'AKShare') if isinstance(macro, dict) else '数据不可用'}

## 情绪与资金面

- 综合情绪: **{composite.get('overall', '数据不可用')}** | {', '.join(composite.get('details', [])) or ''}
- 北向资金净流向: {_fmt_northbound(nb)} [{nb.get('source', '')}] (日期: {nb.get('date', '')})
- 北向5日累计: {_fmt_value_optional(nb.get('net_flow_5d_yi'), '亿')}
- 全市场上涨占比: {_fmt_ratio(breadth.get('up_ratio'))} | {breadth.get('signal', '')} [{breadth.get('source', '')}]
- 情绪数据来源: {sentiment.get('source', '') if isinstance(sentiment, dict) else '数据不可用'}

## 核心事实

- 最新价: {etf.get('current_price')} [{etf.get('source') or '来源缺失'}] (数据日期: {etf.get('last_date', '未知')})
- 当日涨跌: {_fmt_percent(etf.get('change_pct'))}
- 近 20 日 / 60 日涨跌: {_fmt_percent(etf.get('return_20d'))} / {_fmt_percent(etf.get('return_60d'))}
- 相对沪深 300 强弱 (20日/60日): {_fmt_delta(rec.get('relative_strength_20d'))} / {_fmt_delta(rec.get('relative_strength_60d'))}
- 20 日 / 60 日 / 120 日均线: {_fmt_value(etf.get('ma20'))} / {_fmt_value(etf.get('ma60'))} / {_fmt_value(etf.get('ma120'))}
- 52周回撤: {_fmt_percent(etf.get('drawdown_from_52w_high_pct'))}
- 所属行业当日涨跌: {_fmt_percent(industry.get('change_pct'))} [{industry.get('source') or '来源缺失'}]
- 行业内部上涨占比: {_fmt_ratio(industry.get('positive_ratio'))} | 上涨 {industry.get('up_count')} / 下跌 {industry.get('down_count')}
- 行业领涨股: {_fmt_leader(industry.get('leader_name'), industry.get('leader_change_pct'))}
- 市场状态: {market.get('regime')} | {market.get('summary')}

## 打分拆解

| 维度 | 分数 | 权重 | 说明 |
|------|------|------|------|
| 趋势 | {rec.get('trend_score')} | 30% | 价格结构与中短期均线 |
| 相对强弱 | {rec.get('relative_strength_score')} | 25% | 是否跑赢沪深 300 |
| 行业扩散 | {rec.get('breadth_score')} | 20% | 行业涨跌家数与板块走势 |
| 量能 | {rec.get('flow_score')} | 10% | 量比与成交额活跃度 |
| 宏观顺风 | {rec.get('macro_tailwind_score')} | 10% | 宏观环境对该行业的友好度 |
| 情绪 | {rec.get('sentiment_score')} | 5% | 北向资金+市场宽度+融资信号 |
| **综合** | **{rec.get('total_score')}** | **100%** | |
| 风险 | {rec.get('risk_score')} | — | 波动、回撤、宏观逆风与市场环境 |

## 交易计划

- 入场触发: {rec.get('entry_trigger')}
- 仓位建议: {rec.get('position_size')}
- 失效条件: {rec.get('exit_trigger')}
- 观察周期: {rec.get('holding_period')}

## 信号摘要

{_render_reasons(rec.get('reasons', []))}

## 数据质量

{_render_missing_data(rec.get('missing_data', []))}

## 相关快讯 {freshness_note}

{news_block}{llm_block}

---

*免责声明: 本项目输出为规则化分析与可选 AI 解读，不构成投资建议。数据来自公开来源（东方财富、AKShare），分析逻辑基于规则化模型。*
"""


def render_universe_report(
    bundle: dict, top_n: int = 5, llm_text: str | None = None
) -> str:
    ranked = bundle.get("ranked", [])[:top_n]
    market = bundle.get("market", {})
    macro = bundle.get("macro", {})
    sentiment = bundle.get("sentiment", {})
    briefs = bundle.get("briefs", {}).get("items", [])

    macro_regime = macro.get("macro_regime", {}) if isinstance(macro, dict) else {}
    composite = sentiment.get("composite_signal", {}) if isinstance(sentiment, dict) else {}

    rows = []
    for item in ranked:
        rec = item.get("recommendation", {})
        etf = item.get("etf", {})
        rows.append(
            f"| {item.get('rank')} | {item.get('name')} | {item.get('symbol')} | "
            f"{item.get('theme')} | {rec.get('rating')} | {rec.get('total_score')} | "
            f"{_fmt_percent(etf.get('return_20d'))} | "
            f"{_fmt_delta(rec.get('relative_strength_20d'))} | "
            f"{rec.get('macro_tailwind_score')} | {rec.get('action')} |"
        )
    table = "\n".join(rows) or "| - | - | - | - | - | - | - | - | - | - |"

    briefs_block = "\n".join(
        f"- {item.get('published') or '日期缺失'} | {item.get('title')}"
        for item in briefs[:6]
    ) or "- 近一周未获取到市场快讯"

    top_cards = "\n".join(_render_top_card(item) for item in ranked[:3])
    llm_block = f"\n\n## AI 市场综述\n\n{llm_text}\n" if llm_text else ""

    return f"""# 行业 ETF 实时轮动建议

**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
**扫描范围**: {len(bundle.get('ranked', []))} 只默认行业 ETF

---

## 宏观环境

- 宏观定位: **{macro_regime.get('regime', '数据不可用')}** | {macro_regime.get('regime_label', '')}
- 宏观摘要: {macro.get('macro_summary', '数据不可用') if isinstance(macro, dict) else '数据不可用'}
- 整体情绪: {composite.get('overall', '数据不可用')}
- 数据来源: {macro.get('source', 'AKShare') if isinstance(macro, dict) else ''}

## 市场状态

- 市场状态: **{market.get('regime')}** | {market.get('summary')}
- 成长 vs 价值 (20 日): {_fmt_delta(market.get('growth_vs_value', {}).get('spread_20d'))}

## 排名总表

| 排名 | ETF | 代码 | 主题 | 评级 | 综合分 | 20日收益 | 相对沪深300 | 宏观顺风 | 执行动作 |
|------|-----|------|------|------|--------|-----------|-------------|----------|----------|
{table}

## 当前重点跟踪

{top_cards}

## 市场快讯

{briefs_block}{llm_block}

---

*免责声明: 本项目输出为规则化分析与可选 AI 解读，不构成投资建议。数据来自公开来源（东方财富、AKShare）。*
"""


# ═════════════════════════════════════════════
# 格式化辅助函数
# ═════════════════════════════════════════════

def _fmt_ratio(value: float | None) -> str:
    if value is None:
        return "数据不可用"
    return f"{value * 100:.1f}%"


def _fmt_percent(value: float | None) -> str:
    if value is None:
        return "数据不可用"
    return f"{value:.1f}%"


def _fmt_delta(value: float | None) -> str:
    if value is None:
        return "数据不可用"
    return f"{value:+.1f}pct"


def _fmt_value(value: float | None) -> str:
    if value is None:
        return "数据不可用"
    return f"{value:.3f}"


def _fmt_value_optional(value: float | None, unit: str = "") -> str:
    if value is None:
        return "数据不可用"
    return f"{value:.1f}{unit}"


def _fmt_leader(name: str | None, change_pct: float | None) -> str:
    if not name:
        return "数据不可用"
    if change_pct is None:
        return name
    return f"{name} ({change_pct:.1f}%)"


def _fmt_northbound(nb: dict) -> str:
    if not isinstance(nb, dict):
        return "数据不可用"
    net = nb.get("net_flow_yi")
    if net is None:
        return "数据不可用"
    direction = "净流入" if net > 0 else "净流出" if net < 0 else "持平"
    return f"{direction} {abs(net):.1f}亿 | {nb.get('signal', '')}"


def _render_reasons(reasons: list[str]) -> str:
    if not reasons:
        return "- 无"
    return "\n".join(f"- {item}" for item in reasons)


def _render_missing_data(items: list[str]) -> str:
    if not items:
        return "- 无明显缺口"
    return "\n".join(f"- {item}" for item in items)


def _render_top_card(item: dict) -> str:
    rec = item.get("recommendation", {})
    etf = item.get("etf", {})
    industry = item.get("industry", {})
    return (
        f"### {item.get('rank')}. {item.get('name')} ({item.get('symbol')}) — {item.get('theme')}\n"
        f"- 评级: **{rec.get('rating')}** | 综合分: {rec.get('total_score')} | 仓位: {rec.get('position_size')}\n"
        f"- 近 20 日收益: {_fmt_percent(etf.get('return_20d'))} | 相对沪深300: {_fmt_delta(rec.get('relative_strength_20d'))}\n"
        f"- 行业上涨占比: {_fmt_ratio(industry.get('positive_ratio'))} | 宏观顺风: {rec.get('macro_tailwind_score')}分\n"
        f"- 当前动作: {rec.get('action')}\n"
    )
