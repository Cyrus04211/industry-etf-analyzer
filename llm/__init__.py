from llm.client import call_llm
from llm.prompts import (
    build_single_etf_prompt,
    build_universe_prompt,
    CREDIBILITY_RULES,
    INDUSTRY_ALPHA_SYSTEM,
    ETF_SYSTEM_PROMPT,
    MACRO_POSITIONING_PROMPT,
    CONSENSUS_DIAGNOSIS_PROMPT,
    VARIANT_PERCEPTION_PROMPT,
    ALLOCATION_DECISION_PROMPT,
)

__all__ = [
    "call_llm",
    "build_single_etf_prompt",
    "build_universe_prompt",
    "CREDIBILITY_RULES",
    "INDUSTRY_ALPHA_SYSTEM",
    "ETF_SYSTEM_PROMPT",
    "MACRO_POSITIONING_PROMPT",
    "CONSENSUS_DIAGNOSIS_PROMPT",
    "VARIANT_PERCEPTION_PROMPT",
    "ALLOCATION_DECISION_PROMPT",
]
