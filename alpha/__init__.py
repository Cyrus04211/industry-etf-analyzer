"""
行业 ETF Alpha 推理管线 — 4 阶段对抗式推理

流程: 宏观定位 -> 共识诊断 -> 变体认知 -> 配置决策
每个后续阶段都可以引用和挑战前序阶段的结论。

与个股分析的6阶段管线相比，行业分析简化到4阶段:
- 不做Barra因子定位（行业ETF关注板块轮动，非个股因子暴露）
- 不做压力测试的因子风险分解
- 聚焦行业特有的宏观敏感性、产业链位置、政策周期
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
    data_snapshot: str,
    model: str | None = None,
    verbose: bool = True,
) -> dict:
    """
    执行完整的 4 阶段行业轮动推理管线。
    返回各阶段的输出 dict。
    """
    symbol = payload.get("symbol", "Unknown")
    name = payload.get("name", "")
    results = {"symbol": symbol, "name": name}

    # Stage 1: 宏观环境与风格定位
    if verbose:
        console.print(
            "\n[bold cyan]Stage 1/4: 宏观环境定位 — 判断当前宏观对哪些行业友好[/bold cyan]"
        )
    try:
        macro_positioning = run_macro_positioning(payload, data_snapshot, model)
        results["macro_positioning"] = macro_positioning
        if verbose:
            console.print("  [green]OK[/green] 宏观定位报告已生成")
    except Exception as e:
        results["macro_positioning"] = f"[错误] {e}"
        if verbose:
            console.print(f"  [red]FAIL[/red] 宏观定位失败: {e}")

    # Stage 2: 行业共识诊断
    if verbose:
        console.print(
            "\n[bold yellow]Stage 2/4: 行业共识诊断 — 市场在定价什么行业逻辑？[/bold yellow]"
        )
    try:
        consensus = run_industry_consensus(
            payload, results.get("macro_positioning", ""), data_snapshot, model
        )
        results["consensus"] = consensus
        if verbose:
            console.print("  [green]OK[/green] 行业共识地图已生成")
    except Exception as e:
        results["consensus"] = f"[错误] {e}"
        if verbose:
            console.print(f"  [red]FAIL[/red] 共识诊断失败: {e}")

    # Stage 3: 变体认知
    if verbose:
        console.print(
            "\n[bold yellow]Stage 3/4: 变体认知 — 行业轮动中市场可能错在哪？[/bold yellow]"
        )
    try:
        variant = run_variant_perception(
            payload,
            results.get("consensus", ""),
            results.get("macro_positioning", ""),
            data_snapshot,
            model,
        )
        results["variant"] = variant
        if verbose:
            console.print("  [green]OK[/green] 认知偏差清单已生成")
    except Exception as e:
        results["variant"] = f"[错误] {e}"
        if verbose:
            console.print(f"  [red]FAIL[/red] 变体认知失败: {e}")

    # Stage 4: 配置决策
    if verbose:
        console.print(
            "\n[bold yellow]Stage 4/4: 行业配置决策 — 综合判断[/bold yellow]"
        )
    try:
        decision = run_allocation_decision(
            payload,
            results.get("consensus", ""),
            results.get("variant", ""),
            results.get("macro_positioning", ""),
            data_snapshot,
            model,
        )
        results["decision"] = decision
        if verbose:
            console.print("  [green]OK[/green] 配置决策书已生成")
    except Exception as e:
        results["decision"] = f"[错误] {e}"
        if verbose:
            console.print(f"  [red]FAIL[/red] 配置决策失败: {e}")

    return results
