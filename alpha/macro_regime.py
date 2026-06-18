"""
Stage 1: 宏观环境与风格定位 — 判断当前宏观对哪些行业友好
"""
from __future__ import annotations

from llm.client import call_llm
from llm.prompts import (
    INDUSTRY_ALPHA_SYSTEM,
    MACRO_POSITIONING_PROMPT,
)


def run_macro_positioning(
    payload: dict, data_snapshot: str, model: str | None = None
) -> str:
    """Stage 1: 宏观环境定位 + LLM 解读"""

    prompt = MACRO_POSITIONING_PROMPT.format(
        name=payload.get("name", ""),
        symbol=payload.get("symbol", ""),
        theme=payload.get("theme", ""),
        board_name=payload.get("board_name", ""),
        data_context=data_snapshot,
    )

    return call_llm(
        system_prompt=INDUSTRY_ALPHA_SYSTEM,
        user_prompt=prompt,
        model=model,
        temperature=0.4,
    )
