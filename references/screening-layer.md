# 筛选层 —— 量化快扫 + 信号探测

> 在执行九步深层穿透之前，必须完成量化筛选。不替代穿透层——只做"该不该继续看"的判断。
> 不同市场走不同通道，但**没有跳过这一层的选项**。

## 市场检测（自动）

技能主入口收到标的名称后，第一步自动判断市场：

| 代码特征 | 市场 | 筛选通道 | 工具 |
|---------|------|---------|------|
| 60xxxx / 00xxxx / 30xxxx / 688xxx | A股 | tdx快扫 | `tdx_quotes` + `tdx_kline` |
| hkxxxxx | 港股 | tdx快扫 | `tdx_quotes target=1` |
| 纯英文ticker (AAPL/TSLA) | 美股 | stock-analysis | `analyze_stock.py --fast` |
| 其他 | 手动判断 | 手工输入代码 | — |

## 通道A：美股（stock-analysis）

```bash
# 加载 stock-analysis skill，执行以下命令：

# 快速量化扫描（--fast 跳过内幕交易+新闻，2-3秒）
uv run {baseDir}/scripts/analyze_stock.py <ticker> --fast

# 传闻/内幕扫描
python3 {baseDir}/scripts/rumor_scanner.py

# 热力扫描（批量选股）
python3 {baseDir}/scripts/hot_scanner.py
```

> ⚠️ stock-analysis 脚本（analyze_stock.py / rumor_scanner.py / hot_scanner.py）基于 Yahoo Finance API，**仅适用美股和加密货币。不可用于A股/港股。**

美股筛选通过标准：

| 指标 | 阈值 | 通过条件 |
|------|------|---------|
| 8维量化综合评分 | 0-100 | ≥60 |
| 风险标记数 | 0-5 | ≤2 |
| 传闻信号 | M&A/内幕 | 记录但不阻断 |

## 通道B：A股/港股（通达信等效快扫）

> stock-analysis 不覆盖A股/港股。以下使用通达信 MCP 工具做等效快扫。

### 步骤1：实时行情 + 基础指标

```
tdx_quotes code="<代码>" setcode="<市场代码>"
→ 提取：最新价、PE(TTM)、总市值、换手率、量比
```

### 步骤2：近20日K线（判断异常波动）

```
tdx_kline code="<代码>" setcode="<市场代码>" period="4" wantNum="20"
→ 计算：近5日涨跌幅、近20日振幅、成交量异常放大的日期
```

### 步骤3：快速排雷清单

| 信号 | 工具 | 阈值 | 标记 |
|------|------|------|:--:|
| PE > 100x 且近两季利润连续下滑 | tdx_quotes + 财报 | — | ⚫ |
| 近5日涨幅 > 15% | tdx_kline计算 | >15% | ⚠️ |
| 换手率 > 10% | tdx_quotes | >10% | ⚠️ |
| 近20日最大振幅 > 30% | tdx_kline计算 | >30% | ⚠️ |
| 股息率 = 0 且 PE > 50x | tdx_quotes | — | ⚠️ |
| 市值 < 50亿 或 < 100亿+无机构持仓 | tdx_quotes | — | ⚠️ |

### 步骤4：选股器快扫（批量场景）

```
tdx_screener message="<选股条件>" rang="AG"
→ 对扫描结果逐一执行步骤1-3
```

---

## 筛选结论模板（两个通道统一输出）

```
【筛选层结论】
标的：<名称/代码>
市场：A股/港股/美股
数据源：tdx / stock-analysis
排雷结果：⚠️ X个 / ⚫ X个（列举）
筛选结论：✅进入穿透层 / ⚠️有条件进入(标注) / ❌跳过(原因)
```

> 筛选层不阻断——只是标注。即使 ⚫ 标记的标的也可选择进入穿透层，但会在穿透报告反偏见声明中明确标注筛选层发现的风险信号。唯一的例外是：**用户主动要求"快速排雷"模式时**，⚫≥2个会自动跳过。

## stock-analysis 脚本适配说明

stock-analysis 的 `analyze_stock.py` 基于 Yahoo Finance (yfinance)，硬编码美股ticker格式。该脚本**不适合改造适配A股**，原因：

1. A股代码格式（6位数字）与美股ticker（字母）完全不同
2. A股财报披露格式是CSRC标准，不是SEC EDGAR
3. A股没有Short Interest/Put-Call Ratio/VIX等美股独有指标

**结论**：A股筛选走通达信通道（tdx_quotes + tdx_kline + tdx_screener），不尝试改造stock-analysis脚本。两个通道并行、独立、各管各的市场。
