"""Stage 1: 宏观环境与风格定位"""
from __future__ import annotations
from llm.client import call_llm
from llm.prompts import INDUSTRY_ALPHA_SYSTEM, MACRO_POSITIONING_PROMPT


def run_macro_positioning(payload: dict, data_context: str, model: str | None = None) -> str:
    prompt = MACRO_POSITIONING_PROMPT.format(
        name=payload.get("name", ""),
        symbol=payload.get("symbol", ""),
        theme=payload.get("theme", ""),
        board_name=payload.get("board_name", ""),
        data_context=data_context,
    )
    return call_llm(system_prompt=INDUSTRY_ALPHA_SYSTEM, user_prompt=prompt, model=model, temperature=0.4)
