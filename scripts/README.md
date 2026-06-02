# 筛选层脚本 —— 市场适配架构

## 设计原则

三层架构中，每一层对三个市场（美股/A股/港股）都有独立的执行通道。脚本位于对应市场目录下。

## 目录结构

```
scripts/
├── screening/                    ← 筛选层（Layer 0）
│   ├── README.md                 ← 本文件
│   ├── us_analyze_stock.py      ← 美股：调用 stock-analysis skill（analyze_stock.py --fast）
│   ├── us_rumor_scanner.py      ← 美股：M&A传闻/内幕交易扫描
│   ├── us_hot_scanner.py        ← 美股：热力扫描批量发现
│   ├── a_share_screener.py      ← A股：通达信快扫 + 排雷清单
│   └── hk_screener.py           ← 港股：通达信快扫（target=1）+ 排雷清单
│
├── penetration/                  ← 穿透层（Layer 1）— 无市场特定脚本
│   （九步框架+蹲站+追问是市场无关的方法论，
│     数据源按市场走：A股→tdx/neodata，美股→stock-analysis，港股→tdx）
│
└── charting/                     ← 报告层（Layer 2）— 无市场特定脚本
    ├── gen_report_pdf.py        ← MD→PDF+PNG（市场无关）
    └── *_backtest_viz.py        ← 回测图表（OHLCV输入，市场无关）
```

## 各市场通道对照

| 层 | 美股 | A股 | 港股 |
|----|------|------|------|
| **筛选层** | stock-analysis skill | `a_share_screener.py`（tdx MCP） | `hk_screener.py`（tdx MCP target=1） |
| **穿透层** | 九步+蹲站（数据源：stock-analysis） | 九步+蹲站（数据源：tdx/neodata） | 九步+蹲站（数据源：tdx target=1） |
| **报告层** | gen_report_pdf + backtest_viz | 同左 | 同左 |

> 筛选层脚本复用 stock-analysis 的产出格式（8维评分/风险标记/传闻信号），A股/港股脚本使用通达信等效替代。

## 筛选层输出规范（三个市场统一）

每个筛选脚本必须输出以下结构化数据：

```json
{
  "ticker": "688206 / AAPL / 01810",
  "market": "A / US / HK",
  "pe_ttm": -321.4,
  "pe_static": 450,
  "market_cap_cny": 15800000000,
  "revenue_yoy": -0.15,
  "profit_yoy": -0.95,
  "score_8dim": null,
  "risk_flags": ["PE亏损", "20日振幅>40%", "股息0+PE>50x"],
  "rumor_signals": [],
  "pass": "conditional"
}
```

## A股等效映射

stock-analysis 的 8 维评分中，A 股通过 tdx 可等效实现的维度：

| stock-analysis 维度 | A股等效数据源 | 可行性 |
|-------------------|-------------|:--:|
| 盈利（30%） | tdx_indicator_select → ROE/净利率/毛利率 | ✅ |
| 基本面（20%） | tdx_api_data → 三大报表 | ✅ |
| 分析师（20%） | tdx_api_data → 研报评级一致预期 | ✅ |
| 动量（15%） | tdx_kline → 近N日涨跌幅 | ✅ |
| 风险（10%） | tdx_quotes → 振幅/换手率 | ✅ |
| 股息（5%） | tdx_quotes ExtInfo.MGGX | ✅ |
| 情绪（—） | 无等效（VIX/Put-Call无A股对应） | ❌ 降级 |
| 内幕（—） | 无等效（SEC EDGAR无A股对应） | ❌ 降级 |

> 映射不完全——评分仅供穿透层反偏见参考，不作为进入/跳过的唯一依据。

## 股票市场分析行业术语

三类市场有各自的专属分析指标和术语：

| 指标 | 美股 | A股 | 港股 |
|------|------|------|------|
| 成交量 | Volume (shares) | 成交量（手，1手=100股） | 成交量（股） |
| 做空 | Short Interest / Put-Call | 融券余量 | 沽空比率 |
| 估值 | Forward PE (华尔街共识) | 动态PE（基于已披露季报年化） | 类似A股 |
| 分红 | Dividend Yield (季度) | 股息率（年度） | 股息率（半年度） |
| 机构持仓 | 13F (SEC强制披露) | 基金重仓（季报披露） | 类似A股 |
| 流动性指标 | VIX / Put-Call Ratio | 换手率 / 量比 | 类似A股 |
| 内部交易 | Form 4 (SEC强制披露) | 大股东增减持公告 | 权益披露（港交所） |

> 在使用不同市场筛选脚本时，必须使用对应市场的术语和指标，不可混用。例如：A股不用 Short Interest，美股不用 融券余量。
