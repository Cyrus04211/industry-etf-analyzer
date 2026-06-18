# 行业 ETF 实时投资建议工具

基于多维度数据采集和对抗式推理的 A 股行业 ETF 轮动分析工具。融合宏观背景、市场情绪、资金流向、行业扩散度和价格趋势，输出结构化的配置建议。

## 功能

- **全维度数据采集**：ETF 行情趋势、行业板块扩散、市场风格轮动、宏观背景（PMI/M2/利率）、情绪与资金流（北向资金、融资融券、市场宽度）
- **规则化评分**：6 维度加权打分（趋势30% + 相对强弱25% + 行业扩散20% + 量能10% + 宏观顺风10% + 情绪5%），风险约束调整
- **可选对抗式推理**（`--alpha`）：4 阶段对抗式推理管线（宏观定位 -> 共识诊断 -> 变体认知 -> 配置决策），含 L1-L4 可信度等级
- **多模式输出**：单ETF深度分析 / 全行业轮动扫描 / JSON结构化输出 / Markdown报告保存

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 可选：配置 LLM（用于 AI 扩展解读和对抗式推理）
cp .env.example .env
# 编辑 .env 填入 DEEPSEEK_API_KEY

# 3. 扫描默认行业 ETF 观察池
python agent.py

# 仅看前 3 名
python agent.py --top 3

# 分析单只行业 ETF
python agent.py 512480

# 单只 ETF + 对抗式推理（需 LLM）
python agent.py 512480 --alpha

# 仅输出 JSON
python agent.py 512480 --json

# 保存报告
python agent.py --save
python agent.py 512480 --save
```

## 配置

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `DEEPSEEK_API_KEY` | (可选) DeepSeek API Key | - |
| `DEEPSEEK_BASE_URL` | API 地址 | `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | 模型 | `deepseek-v4-flash` |
| `ETF_NEWS_MAX_ITEMS` | 快讯最大条数 | `8` |
| `ETF_NEWS_MAX_DAYS` | 快讯最大天数 | `7` |
| `FINNHUB_API_KEY` | (可选) 全球市场情绪 | - |
| `FRED_API_KEY` | (可选) 美国宏观数据 | - |

## 项目结构

```text
├── agent.py              # 主入口 CLI
├── config.py             # 全局配置（从 .env 读取）
├── requirements.txt
├── data/                 # 数据采集层
│   ├── price.py          # ETF 实时行情与历史趋势
│   ├── industry.py       # 行业/概念板块表现与扩散
│   ├── market.py         # 大盘环境与风格轮动（基准ETF）
│   ├── macro.py          # 宏观经济背景（PMI/CPI/M2/Shibor）
│   ├── sentiment.py      # 市场情绪与资金流（北向/融资/宽度）
│   ├── news.py           # 市场快讯筛选（含7日新鲜度过滤）
│   ├── freshness.py      # 叙事数据新鲜度工具
│   ├── resolver.py       # 结构化快照 + 核心事实摘要
│   ├── universe.py       # 默认行业 ETF 观察池（12只）
│   └── utils.py          # 通用工具（Eastmoney API等）
├── alpha/                # Alpha 推理管线（4阶段对抗式）
│   ├── macro_regime.py   # Stage 1: 宏观环境与风格定位
│   ├── consensus.py      # Stage 2: 行业共识诊断
│   ├── variant.py        # Stage 3: 变体认知
│   └── decision.py       # Stage 4: 行业配置决策
├── strategy/             # 策略层
│   ├── scoring.py        # 6维度规则化打分引擎
│   └── report.py         # Markdown 报告输出
├── llm/                  # LLM 客户端
│   ├── client.py         # DeepSeek API 调用
│   └── prompts.py        # 系统提示词（含L1-L4可信度框架）
└── tests/                # 测试
    ├── test_scoring.py
    └── test_data_parsers.py
```

## 评分逻辑

默认扫描模式输出行业 ETF 排名表，核心排序由六类信号加权组成：

1. **趋势得分 (30%)**：价格相对均线、20/60日收益。
2. **相对强弱得分 (25%)**：ETF 是否跑赢沪深 300。
3. **行业扩散得分 (20%)**：板块涨跌幅、上涨家数占比。
4. **量能得分 (10%)**：成交量比、成交额比。
5. **宏观顺风得分 (10%)**：基于 PMI/M2/利率/风格判断行业宏观友好度。
6. **情绪得分 (5%)**：北向资金流向、市场宽度、融资信号。

再用风险得分做约束，避免对高波动弱趋势标的给出过度激进的评级。

## 对抗式推理（--alpha）

当配置了 LLM 且使用 `--alpha` 参数时，系统对单只 ETF 执行 4 阶段对抗式推理：

1. **宏观定位**：判断当前宏观对该行业的友好度（顺风/逆风/中性）
2. **共识诊断**：反向解构市场在定价什么行业逻辑
3. **变体认知**：系统性寻找共识中的裂缝（每个反证必须标注 L1/L2 数据依据）
4. **配置决策**：综合判断，输出评级+仓位+证伪条件

所有 LLM 输出遵循 L1-L4 可信度纪律：
- L1: 直接从数据提取的事实（标注来源）
- L2: 简单算术计算
- L3: 单步逻辑推断（需写明推理链）
- L4: 综合判断（必须标注置信度）

## 默认观察池

12 只常见行业 ETF，覆盖科技成长、新能源、消费、金融、资源、医药、高端制造等板块。每个条目带有 `board_code` 和 `board_type`，用于直接命中东方财富对应板块。定义在 `data/universe.py`。

## 局限

- 自定义 ETF 若未在观察池中配置 `board_code`，板块扩散信号可能缺失
- 宏观数据依赖 AKShare，若接口不可用时该维度降级
- 第一版没有接入 ETF 申赎、期权隐波、Level-2 资金流等更高频数据
- 对抗式推理质量依赖 LLM 能力，DeepSeek API 不可用时降级为纯规则化分析

## 验证

```bash
python3 -m unittest discover -s tests
```

## 免责声明

本项目输出为程序化分析结果与可选 AI 解读，不构成投资建议。数据来自公开来源（东方财富、AKShare），分析逻辑基于规则化模型。
