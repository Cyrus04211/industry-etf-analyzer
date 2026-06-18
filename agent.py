#!/usr/bin/env python3
"""
行业 ETF 投资分析工具 — 基于 4 阶段对抗式推理

用法:
    python agent.py                  # 扫描默认行业 ETF 观察池
    python agent.py --top 5          # 仅看前 5 名
    python agent.py 512480           # 单只 ETF 深度分析
    python agent.py 512480 --json    # 仅输出聚合数据 JSON
    python agent.py --save           # 保存报告
    python agent.py 512480 --save    # 单只 ETF + 保存报告

流程:
    全维度数据采集 -> 宏观定位 -> 共识诊断 -> 变体认知 -> 配置决策 -> 报告输出
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from config import check_config, DEEPSEEK_MODEL
from data import analyze_symbol, analyze_universe
from data.resolver import build_single_etf_context, build_universe_context
from llm import call_llm, INDUSTRY_ALPHA_SYSTEM, SINGLE_ETF_ANALYSIS_PROMPT, UNIVERSE_RANKING_PROMPT
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

console = Console()
OUTPUT_DIR = Path(__file__).parent / "output"


def parse_args():
    parser = argparse.ArgumentParser(description="行业 ETF 投资分析工具")
    parser.add_argument("symbol", nargs="?", help="ETF 代码；留空则扫描默认行业 ETF 观察池")
    parser.add_argument("--top", type=int, default=5, help="扫描模式下输出前 N 名")
    parser.add_argument("--json", action="store_true", help="仅输出聚合数据 JSON，不调用 LLM")
    parser.add_argument("--save", action="store_true", help="将报告保存到 output/ 目录")
    parser.add_argument("--model", type=str, default=None, help="覆盖默认模型")
    return parser.parse_args()


def main():
    args = parse_args()

    # 检查 LLM 配置
    if not args.json:
        ok = check_config()
        if not ok:
            console.print("\n[red]请先配置 DeepSeek API Key:[/red]")
            console.print("  方式 1: 创建 .env 文件，写入 DEEPSEEK_API_KEY=sk-xxx")
            console.print("  方式 2: export DEEPSEEK_API_KEY=sk-xxx")
            console.print("  方式 3: 使用 --json 模式仅输出数据\n")
            sys.exit(1)

    if args.symbol:
        _run_single_etf(args)
    else:
        _run_universe_scan(args)


def _run_single_etf(args):
    """单只 ETF 深度分析 — 4 阶段对抗式推理"""
    symbol = args.symbol.strip()

    console.print(Panel.fit(
        f"[bold white]行业 ETF 深度分析[/bold white]\n"
        f"代码: [yellow]{symbol}[/yellow]  |  "
        f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"[dim]4 阶段对抗式推理: 宏观定位 -> 共识诊断 -> 变体认知 -> 配置决策[/dim]",
        border_style="cyan",
    ))

    # 第一步: 拉取全维度数据
    payload = analyze_symbol(symbol, verbose=not args.json)

    if args.json:
        console.print_json(json.dumps(payload, ensure_ascii=False, default=str))
        return

    data_context = build_single_etf_context(payload)

    # 第二步: 4 阶段对抗式推理
    from alpha import run_industry_alpha_pipeline

    console.print("\n[bold cyan]启动 4 阶段对抗式推理...[/bold cyan]")
    console.print("[dim]Stage 1 (宏观定位) 判断宏观对该行业的友好度，后续 3 阶段互相挑战[/dim]")

    try:
        results = run_industry_alpha_pipeline(
            payload=payload,
            data_context=data_context,
            model=args.model,
            verbose=True,
        )
    except Exception as e:
        console.print(f"[red]推理管线执行失败: {e}[/red]")
        sys.exit(1)

    # 第三步: 组装报告
    report = _assemble_single_report(payload, results)

    console.print("\n" + "=" * 80)
    console.print(Markdown(report))
    console.print("=" * 80)

    if args.save:
        _save_report(payload.get("symbol", symbol), report)

    console.print(
        "\n[dim]免责声明: 本报告由 AI 通过对抗式推理自动生成，数据来自公开来源（东方财富、AKShare）。"
        "所有分析仅代表一种分析视角，不构成投资建议。[/dim]"
    )


def _run_universe_scan(args):
    """行业轮动扫描 — LLM 驱动排名 + 分析"""
    console.print(Panel.fit(
        f"[bold white]行业 ETF 轮动扫描[/bold white]\n"
        f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"[dim]方法: 全维度数据采集 -> LLM 驱动排名 -> 行业轮动建议[/dim]",
        border_style="cyan",
    ))

    # 第一步: 拉取全市场数据
    bundle = analyze_universe(verbose=not args.json)

    if args.json:
        console.print_json(json.dumps(bundle, ensure_ascii=False, default=str))
        return

    # 第二步: LLM 排名 + 分析
    universe_context = build_universe_context(bundle, top_n=args.top * 2)

    # 分离宏观背景和 ETF 表格，分两次注入以减少单次 prompt 长度
    context_data = json.loads(universe_context)
    macro_context = json.dumps({
        "分析时间": context_data.get("分析时间"),
        "扫描ETF数量": context_data.get("扫描ETF数量"),
        "宏观环境": context_data.get("宏观环境"),
        "市场环境": context_data.get("市场环境"),
        "情绪资金面": context_data.get("情绪资金面"),
    }, ensure_ascii=False, indent=2)

    etf_table = json.dumps(context_data.get("ETF指标总表", []), ensure_ascii=False, indent=2)

    prompt = UNIVERSE_RANKING_PROMPT.format(
        macro_context=macro_context,
        etf_table=etf_table,
    )

    console.print("\n[bold cyan]LLM 正在进行行业轮动分析...[/bold cyan]")

    try:
        llm_analysis = call_llm(
            system_prompt=INDUSTRY_ALPHA_SYSTEM,
            user_prompt=prompt,
            model=args.model,
            temperature=0.5,
            max_tokens=8192,
        )
    except Exception as e:
        console.print(f"[red]LLM 分析失败: {e}[/red]")
        sys.exit(1)

    # 第三步: 组装报告
    report = _assemble_universe_report(bundle, llm_analysis, args.top)

    console.print("\n" + "=" * 80)
    console.print(Markdown(report))
    console.print("=" * 80)

    if args.save:
        _save_report("universe", report)

    console.print(
        "\n[dim]免责声明: 本报告由 AI 自动生成，数据来自公开来源（东方财富、AKShare）。"
        "不构成投资建议。[/dim]"
    )


def _assemble_single_report(payload: dict, results: dict) -> str:
    """组装单只 ETF 的最终报告（参照 个股分析 模式）"""
    etf = payload.get("etf", {})
    industry = payload.get("industry", {})
    market = payload.get("market", {})

    def _fmt(v, suffix=""):
        if v is None:
            return "数据不可用"
        return f"{v}{suffix}"

    report = f"""# 行业 ETF 深度分析 | {payload.get('name')} ({payload.get('symbol')})

**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
**所属主题**: {payload.get('theme')}
**对应行业板块**: {payload.get('board_name') or '未映射'}
**当前价格**: {_fmt(etf.get('current_price'), ' 元')} [{etf.get('source') or '--'}]
**当日涨跌**: {_fmt(etf.get('change_pct'), '%')}
**近20日收益**: {_fmt(etf.get('return_20d'), '%')}
**近60日收益**: {_fmt(etf.get('return_60d'), '%')}
**分析方法**: 4 阶段对抗式推理

---

## 一、宏观环境与风格定位

{results.get('macro_positioning', '[未生成]')}

---

## 二、行业共识诊断

{results.get('consensus', '[未生成]')}

---

## 三、变体认知分析

{results.get('variant', '[未生成]')}

---

## 四、行业配置决策

{results.get('decision', '[未生成]')}

---

## 附录A：核心原始数据

| 指标 | 数值 | 来源 |
|------|------|------|
| 最新价 | {_fmt(etf.get('current_price'))} | {etf.get('source', '--')} |
| 20日均线 | {_fmt(etf.get('ma20'))} | {etf.get('source', '--')} |
| 60日均线 | {_fmt(etf.get('ma60'))} | {etf.get('source', '--')} |
| 20日波动率(年化) | {_fmt(etf.get('volatility_20d'), '%')} | {etf.get('source', '--')} |
| 近5日收益 | {_fmt(etf.get('return_5d'), '%')} | {etf.get('source', '--')} |
| 年内收益 | {_fmt(etf.get('return_ytd'), '%')} | {etf.get('source', '--')} |
| 行业上涨占比 | {_fmt(industry.get('positive_ratio'))} | {industry.get('source', '--')} |
| 行业领涨股 | {industry.get('leader_name', '--')} ({_fmt(industry.get('leader_change_pct'), '%')}) | {industry.get('source', '--')} |
| 市场状态 | {market.get('regime', '--')} | 沪深300ETF行情 |

## 附录B：数据质量

- ETF 数据: {'可用' if etf.get('current_price') else '缺失'}
- 行业板块数据: {'可用' if industry.get('change_pct') is not None else '缺失'}
- 宏观数据: {'可用' if payload.get('macro', {}).get('macro_summary') else '缺失'}
- 情绪数据: {'可用' if payload.get('sentiment', {}).get('composite_signal', {}).get('overall') else '缺失'}

---

*免责声明: 本报告由 AI 通过对抗式推理自动生成，数据来自公开来源。不构成投资建议。*
*生成日期: {datetime.now().strftime('%Y-%m-%d')}*
"""
    return report


def _assemble_universe_report(bundle: dict, llm_analysis: str, top_n: int) -> str:
    """组装行业轮动扫描报告"""
    market = bundle.get("market", {})
    macro = bundle.get("macro", {})
    macro_regime = macro.get("macro_regime", {}) if isinstance(macro, dict) else {}

    report = f"""# 行业 ETF 轮动扫描报告

**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
**扫描范围**: {len(bundle.get('analyses', []))} 只默认行业 ETF
**市场状态**: {market.get('regime')}
**宏观定位**: {macro_regime.get('regime', '未知')}

---

## 宏观环境

- {macro.get('macro_summary', '数据不可用')}
- 市场环境: {market.get('summary', '')}

---

{llm_analysis}

---

## 附录：数据来源

- ETF 行情: 东方财富 ETF Quote + K线历史
- 行业板块: 东方财富板块行情
- 宏观数据: AKShare (PMI/CPI/M2/Shibor)
- 市场情绪: AKShare (北向资金/融资融券/全市场统计)
- 快讯: 东方财富全球快讯

---

*免责声明: 本报告由 AI 自动生成，数据来自公开来源。不构成投资建议。*
*生成日期: {datetime.now().strftime('%Y-%m-%d')}*
"""
    return report


def _save_report(prefix: str, report: str):
    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = OUTPUT_DIR / f"{prefix}_{timestamp}.md"
    filename.write_text(report, encoding="utf-8")
    console.print(f"\n[green]报告已保存至: {filename}[/green]")


if __name__ == "__main__":
    main()
