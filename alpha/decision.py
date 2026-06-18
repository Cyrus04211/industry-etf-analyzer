"""Stage 4: 行业配置决策"""
from __future__ import annotations
from llm.client import call_llm
from llm.prompts import INDUSTRY_ALPHA_SYSTEM, ALLOCATION_DECISION_PROMPT


def run_allocation_decision(payload: dict, consensus_map: str, variant_perception: str, macro_positioning: str, data_context: str, model: str | None = None) -> str:
    prompt = ALLOCATION_DECISION_PROMPT.format(
        name=payload.get("name", ""),
        symbol=payload.get("symbol", ""),
        theme=payload.get("theme", ""),
        board_name=payload.get("board_name", ""),
        consensus_map=consensus_map,
        variant_perception=variant_perception,
        macro_positioning=macro_positioning,
        data_context=data_context,
    )
    return call_llm(system_prompt=INDUSTRY_ALPHA_SYSTEM, user_prompt=prompt, model=model, temperature=0.4)
