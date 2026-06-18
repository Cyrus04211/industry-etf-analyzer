"""
行业 ETF 分析 Agent — 全局配置
"""
import os
from dotenv import load_dotenv

load_dotenv()

# --- DeepSeek API ---
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")

# --- Optional APIs ---
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
FRED_API_KEY = os.getenv("FRED_API_KEY", "")

# --- News ---
ETF_NEWS_MAX_ITEMS = int(os.getenv("ETF_NEWS_MAX_ITEMS", "8"))
ETF_NEWS_MAX_DAYS = int(os.getenv("ETF_NEWS_MAX_DAYS", "7"))


def check_config():
    """检查必需配置是否齐全"""
    issues = []
    if not DEEPSEEK_API_KEY:
        issues.append("DEEPSEEK_API_KEY 未设置 — 请设置环境变量或创建 .env 文件")
    if issues:
        print("[WARN] " + "; ".join(issues))
    return len(issues) == 0
