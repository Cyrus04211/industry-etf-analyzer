"""
Stage 2: 行业共识诊断 — 市场在定价什么行业逻辑？
"""
from __future__ import annotations

from llm.client import call_llm
from llm.prompts import (
    INDUSTRY_ALPHA_SYSTEM,
    CONSENSUS_DIAGNOSIS_PROMPT,
)


def run_industry_consensus(
    payload: dict,
    macro_positioning: str,
    data_snapshot: str,
    model: str | None = None,
) -> str:
    """Stage 2: 诊断市场对该行业的共识"""

    prompt = CONSENSUS_DIAGNOSIS_PROMPT.format(
        name=payload.get("name", ""),
        symbol=payload.get("symbol", ""),
        theme=payload.get("theme", ""),
        board_name=payload.get("board_name", ""),
        macro_positioning=macro_positioning,
        data_context=data_snapshot,
    )

    return call_llm(
        system_prompt=INDUSTRY_ALPHA_SYSTEM,
        user_prompt=prompt,
        model=model,
        temperature=0.5,
    )
