"""
行业 ETF Alpha 推理管线 — 4 阶段对抗式推理

流程: 宏观定位 -> 共识诊断 -> 变体认知 -> 配置决策
每个后续阶段都可以引用和挑战前序阶段的结论。
"""
from __future__ import annotations

from rich.console import Console
from alpha.macro_regime import run_macro_positioning
from alpha.consensus import run_industry_consensus
from alpha.variant import run_variant_perception
from alpha.decision import run_allocation_decision

console = Console()


def run_industry_alpha_pipeline(
    payload: dict,
    data_context: str,
    model: str | None = None,
    verbose: bool = True,
) -> dict:
    """
    执行完整的 4 阶段行业轮动推理管线。
    每个阶段都是独立的 LLM 调用，后续阶段可以挑战前序结论。
    """
    symbol = payload.get("symbol", "Unknown")
    name = payload.get("name", "")
    results = {"symbol": symbol, "name": name}

    # Stage 1: 宏观环境与风格定位
    if verbose:
        console.print(
            "\n[bold cyan]Stage 1/4: 宏观环境定位 — 判断当前宏观对该行业的友好度[/bold cyan]"
        )
    try:
        results["macro_positioning"] = run_macro_positioning(payload, data_context, model)
        if verbose:
            console.print("  [green]OK[/green] 宏观定位完成")
    except Exception as e:
        results["macro_positioning"] = f"[错误] {e}"
        if verbose:
            console.print(f"  [red]FAIL[/red] {e}")

    # Stage 2: 共识诊断
    if verbose:
        console.print(
            "\n[bold yellow]Stage 2/4: 共识诊断 — 市场在定价什么行业逻辑？[/bold yellow]"
        )
    try:
        results["consensus"] = run_industry_consensus(
            payload, results.get("macro_positioning", ""), data_context, model
        )
        if verbose:
            console.print("  [green]OK[/green] 共识地图完成")
    except Exception as e:
        results["consensus"] = f"[错误] {e}"
        if verbose:
            console.print(f"  [red]FAIL[/red] {e}")

    # Stage 3: 变体认知
    if verbose:
        console.print(
            "\n[bold yellow]Stage 3/4: 变体认知 — 寻找共识裂缝[/bold yellow]"
        )
    try:
        results["variant"] = run_variant_perception(
            payload,
            results.get("consensus", ""),
            results.get("macro_positioning", ""),
            data_context,
            model,
        )
        if verbose:
            console.print("  [green]OK[/green] 认知偏差清单完成")
    except Exception as e:
        results["variant"] = f"[错误] {e}"
        if verbose:
            console.print(f"  [red]FAIL[/red] {e}")

    # Stage 4: 配置决策
    if verbose:
        console.print(
            "\n[bold yellow]Stage 4/4: 配置决策 — 综合判断[/bold yellow]"
        )
    try:
        results["decision"] = run_allocation_decision(
            payload,
            results.get("consensus", ""),
            results.get("variant", ""),
            results.get("macro_positioning", ""),
            data_context,
            model,
        )
        if verbose:
            console.print("  [green]OK[/green] 配置决策完成")
    except Exception as e:
        results["decision"] = f"[错误] {e}"
        if verbose:
            console.print(f"  [red]FAIL[/red] {e}")

    return results
