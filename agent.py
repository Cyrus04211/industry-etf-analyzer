#!/usr/bin/env python3
"""
行业 ETF 实时投资建议 CLI — 增强版（含宏观、情绪、对抗式推理）

用法:
    python agent.py                  # 扫描默认行业 ETF 观察池
    python agent.py --top 3          # 仅看前 3 名
    python agent.py 512480           # 单只 ETF 深度分析
    python agent.py 512480 --json    # 仅输出 JSON
    python agent.py --save           # 保存报告
    python agent.py 512480 --save    # 单只 ETF + 保存
    python agent.py 512480 --alpha   # 启用 4 阶段对抗式推理（需 LLM）
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from config import check_config, llm_enabled
from data import analyze_symbol, analyze_universe
from data.resolver import (
    build_enhanced_snapshot,
    build_universe_snapshot,
    facts_summary_for_prompt,
)
from llm import (
    build_single_etf_prompt,
    build_universe_prompt,
    call_llm,
)
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from strategy import render_single_report, render_universe_report

console = Console()
OUTPUT_DIR = Path(__file__).parent / "output"


def parse_args():
    parser = argparse.ArgumentParser(description="行业 ETF 实时投资建议分析")
    parser.add_argument(
        "symbol", nargs="?", help="ETF 代码；留空则扫描默认行业 ETF 观察池"
    )
    parser.add_argument("--top", type=int, default=5, help="扫描模式下输出前 N 名")
    parser.add_argument("--json", action="store_true", help="仅输出结构化 JSON")
    parser.add_argument(
        "--save", action="store_true", help="将 Markdown 报告保存到 output/ 目录"
    )
    parser.add_argument("--model", type=str, default=None, help="覆盖默认 DeepSeek 模型")
    parser.add_argument(
        "--alpha",
        action="store_true",
        help="启用 4 阶段对抗式推理管线（需 LLM，仅单 ETF 模式）",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    llm_ready = check_config()

    console.print(
        Panel.fit(
            f"[bold white]行业 ETF 实时投资建议[/bold white]\n"
            f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  "
            f"模式: {'单只 ETF 深度分析' if args.symbol else '行业轮动扫描'}"
            f"{' + 4阶段对抗式推理' if args.alpha and args.symbol else ''}\n"
            f"[dim]方法: 宏观定位 + 实时行情 + 板块扩散 + 相对强弱 + 情绪资金流 + 风险约束 + 可选对抗式推理[/dim]",
            border_style="cyan",
        )
    )

    if args.symbol:
        payload = analyze_symbol(args.symbol, verbose=not args.json)

        if args.json:
            console.print_json(json.dumps(payload, ensure_ascii=False, default=str))
            return

        # 选择 LLM 解读模式
        llm_text = None
        if llm_ready and llm_enabled():
            if args.alpha:
                llm_text = _run_alpha_pipeline(payload, args.model)
            else:
                llm_text = _maybe_generate_single_llm(payload, args.model)

        report = render_single_report(payload, llm_text=llm_text)
    else:
        payload = analyze_universe(verbose=not args.json)

        if args.json:
            console.print_json(json.dumps(payload, ensure_ascii=False, default=str))
            return

        llm_text = None
        if llm_ready and llm_enabled():
            llm_text = _maybe_generate_universe_llm(payload, args.top, args.model)

        report = render_universe_report(payload, top_n=args.top, llm_text=llm_text)

    console.print()
    console.print(Markdown(report))

    if args.save:
        OUTPUT_DIR.mkdir(exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M")
        prefix = args.symbol or "universe"
        output_file = OUTPUT_DIR / f"{prefix}_{stamp}.md"
        output_file.write_text(report, encoding="utf-8")
        console.print(f"\n[green]报告已保存到: {output_file}[/green]")


def _run_alpha_pipeline(payload: dict, model: str | None = None) -> str | None:
    """执行 4 阶段对抗式推理管线"""
    from alpha import run_industry_alpha_pipeline

    snapshot = build_enhanced_snapshot(payload)
    facts = facts_summary_for_prompt(payload)

    console.print("\n[bold cyan]启动 4 阶段对抗式推理...[/bold cyan]")
    console.print(
        "[dim]宏观定位 -> 共识诊断 -> 变体认知 -> 配置决策（每个阶段可挑战前序结论）[/dim]"
    )

    try:
        results = run_industry_alpha_pipeline(
            payload=payload,
            data_snapshot=f"{facts}\n\n{snapshot}",
            model=model,
            verbose=True,
        )
    except Exception as e:
        console.print(f"[red]对抗式推理执行失败: {e}[/red]")
        return None

    # 组装最终输出
    parts = []
    for stage, title in [
        ("macro_positioning", "## 一、宏观环境与风格定位"),
        ("consensus", "## 二、行业共识诊断"),
        ("variant", "## 三、变体认知分析"),
        ("decision", "## 四、行业配置决策"),
    ]:
        content = results.get(stage, "")
        if content and not str(content).startswith("[错误]"):
            parts.append(f"{title}\n\n{content}")

    if not parts:
        return None

    return "\n\n---\n\n".join(parts)


def _maybe_generate_single_llm(payload: dict, model: str | None) -> str | None:
    try:
        system_prompt, user_prompt = build_single_etf_prompt(payload)
        return call_llm(system_prompt, user_prompt, model=model)
    except Exception as exc:
        console.print(f"[yellow]LLM 扩展解读生成失败: {exc}[/yellow]")
        return None


def _maybe_generate_universe_llm(
    payload: dict, top_n: int, model: str | None
) -> str | None:
    try:
        system_prompt, user_prompt = build_universe_prompt(payload, top_n=top_n)
        return call_llm(system_prompt, user_prompt, model=model)
    except Exception as exc:
        console.print(f"[yellow]LLM 市场综述生成失败: {exc}[/yellow]")
        return None


if __name__ == "__main__":
    main()
