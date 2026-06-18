"""
Stage 3: 变体认知 — 行业轮动中市场可能错在哪？
"""
from __future__ import annotations

from llm.client import call_llm
from llm.prompts import (
    INDUSTRY_ALPHA_SYSTEM,
    VARIANT_PERCEPTION_PROMPT,
)


def run_variant_perception(
    payload: dict,
    consensus_map: str,
    macro_positioning: str,
    data_snapshot: str,
    model: str | None = None,
) -> str:
    """Stage 3: 挑战行业共识，寻找认知偏差"""

    prompt = VARIANT_PERCEPTION_PROMPT.format(
        name=payload.get("name", ""),
        symbol=payload.get("symbol", ""),
        theme=payload.get("theme", ""),
        board_name=payload.get("board_name", ""),
        consensus_map=consensus_map,
        macro_positioning=macro_positioning,
        data_context=data_snapshot,
    )

    return call_llm(
        system_prompt=INDUSTRY_ALPHA_SYSTEM,
        user_prompt=prompt,
        model=model,
        temperature=0.7,  # 更高温度鼓励创造性反证
    )
