"""
行业 ETF 实时分析项目 — 全局配置
"""
from __future__ import annotations

import os

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - 允许在未安装依赖时导入纯函数模块
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()

# --- DeepSeek API ---
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")

# --- 新闻快讯配置 ---
ETF_NEWS_MAX_ITEMS = int(os.getenv("ETF_NEWS_MAX_ITEMS", "8"))
ETF_NEWS_MAX_DAYS = int(os.getenv("ETF_NEWS_MAX_DAYS", "7"))

# --- 可选外部 API ---
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
FRED_API_KEY = os.getenv("FRED_API_KEY", "")


def llm_enabled() -> bool:
    return bool(DEEPSEEK_API_KEY)


def check_config() -> bool:
    """检查 LLM 相关配置；项目本身支持无 LLM 运行。"""
    if llm_enabled():
        return True
    print("[WARN] 未设置 DEEPSEEK_API_KEY，将仅输出规则化建议，不生成 LLM 扩展解读。")
    return False
