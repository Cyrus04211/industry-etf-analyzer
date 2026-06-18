# 行业 ETF 投资分析工具

基于 4 阶段对抗式推理的 A 股行业 ETF 轮动分析工具。融合宏观背景、市场情绪、资金流向、行业扩散和价格趋势，通过 LLM 驱动分析生成结构化配置建议。

## 功能

- **全维度数据采集**：ETF 行情趋势、行业板块扩散、市场风格轮动、宏观背景 (PMI/M2/CPI/Shibor)、情绪与资金流 (北向/融资融券/市场宽度)、新闻快讯 (7日新鲜度过滤)
- **4 阶段对抗式推理**：宏观定位 → 共识诊断 → 变体认知 → 配置决策（每个阶段可挑战前序结论）
- **L1-L4 可信度框架**：每句话标注可信度等级 (L1-事实/L2-计算/L3-推断/L4-综合判断)
- **双模式分析**：单 ETF 深度分析 (4 LLM 调用) / 全行业轮动扫描 (1 LLM 调用)
- **多市场支持**：A 股行业 ETF

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 API Key (必需)
cp .env.example .env
# 编辑 .env 填入 DEEPSEEK_API_KEY=sk-xxx

# 3. 扫描默认行业 ETF 观察池
python agent.py

# 仅看前 5 名
python agent.py --top 5

# 分析单只行业 ETF (4 阶段对抗式推理)
python agent.py 512480

# 仅输出结构化数据 JSON
python agent.py 512480 --json

# 保存报告
python agent.py --save
python agent.py 512480 --save
```

## 配置

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `DEEPSEEK_API_KEY` | (必需) DeepSeek API Key | - |
| `DEEPSEEK_BASE_URL` | API 地址 | `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | 模型 | `deepseek-v4-flash` |
| `ETF_NEWS_MAX_ITEMS` | 快讯最大条数 | `8` |
| `ETF_NEWS_MAX_DAYS` | 快讯最大天数 | `7` |
| `FINNHUB_API_KEY` | (可选) 全球市场情绪 | - |
| `FRED_API_KEY` | (可选) 美国宏观数据 | - |

## 项目结构

```text
├── agent.py              # 主入口 CLI
├── config.py             # 全局配置 (.env)
├── requirements.txt
├── data/                 # 数据采集层
│   ├── price.py          # ETF 实时行情与历史趋势
│   ├── industry.py       # 行业/概念板块表现与扩散
│   ├── market.py         # 大盘环境与风格轮动 (基准ETF)
│   ├── macro.py          # 宏观经济背景 (PMI/CPI/M2/Shibor)
│   ├── sentiment.py      # 市场情绪与资金流 (北向/融资/宽度)
│   ├── news.py           # 市场快讯筛选 (7日新鲜度过滤)
│   ├── freshness.py      # 叙事数据新鲜度工具
│   ├── resolver.py       # LLM prompt 上下文构建
│   ├── universe.py       # 默认行业 ETF 观察池 (12只)
│   └── utils.py          # 通用工具 (Eastmoney API等)
├── alpha/                # Alpha 推理管线 (4阶段对抗式)
│   ├── macro_regime.py   # Stage 1: 宏观环境与风格定位
│   ├── consensus.py      # Stage 2: 行业共识诊断
│   ├── variant.py        # Stage 3: 变体认知
│   └── decision.py       # Stage 4: 行业配置决策
├── llm/                  # LLM 客户端
│   ├── client.py         # DeepSeek API 调用
│   └── prompts.py        # 系统提示词 (含 L1-L4 可信度框架)
└── tests/                # 测试
    └── test_data_parsers.py
```

## 分析管线

### 单 ETF 模式 — 4 阶段对抗式推理

1. **宏观定位** — 判断当前宏观对该行业的友好度 (顺风/逆风/中性)
2. **共识诊断** — 反向解构市场在定价什么行业逻辑
3. **变体认知** — 系统性寻找共识裂缝 (每个反证标注 L1/L2 依据)
4. **配置决策** — 综合判断，输出评级 + 核心逻辑 + 证伪条件

### 行业轮动模式 — LLM 驱动排名

对所有 ETF 全维度指标进行综合排名，输出 Top N 机会 + 轮动方向 + 风险提示。

### 可信度纪律 (L1-L4)

- **L1-事实**: 直接从原始数据提取，可验证
- **L2-计算**: 对 L1 的简单算术运算
- **L3-推断**: 基于 L1/L2 的单步逻辑推断 (需推理链)
- **L4-综合判断**: 多步推断的综合结论 (必须标注置信度)

## 默认观察池

12 只常见行业 ETF，覆盖科技成长、新能源、消费、金融、资源、医药、高端制造等板块。定义在 `data/universe.py`。

## 数据来源

- ETF/板块行情: 东方财富 (Eastmoney API)
- 宏观数据: AKShare (PMI/CPI/M2/Shibor)
- 情绪资金流: AKShare (北向资金/融资融券/市场宽度)
- 快讯: 东方财富全球快讯

## 验证

```bash
python3 -m unittest discover -s tests
python3 -m compileall .
```

## 免责声明

本项目输出为 AI 生成的分析与建议，不构成投资建议。数据来自公开来源。
