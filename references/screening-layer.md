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

## 通道A：美股（stock-analysis skill）

脚本入口：`scripts/screening/us_screener.py`（桥接 stock-analysis）
实际执行：加载 stock-analysis skill → `analyze_stock.py <ticker> --fast`

```bash
# 快速量化扫描（--fast 跳过内幕交易+新闻，2-3秒）
uv run {baseDir}/scripts/analyze_stock.py <ticker> --fast

# 传闻/内幕扫描
python3 {baseDir}/scripts/rumor_scanner.py

# 热力扫描（批量选股）
python3 {baseDir}/scripts/hot_scanner.py
```

> ⚠️ stock-analysis 脚本基于 Yahoo Finance API，**仅适用美股和加密货币。不可用于A股/港股。**

美股筛选通过标准：

| 指标 | 阈值 | 通过条件 |
|------|------|---------|
| 8维量化综合评分 | 0-100 | ≥60 |
| 风险标记数 | 0-5 | ≤2 |
| 传闻信号 | M&A/内幕 | 记录但不阻断 |

## 通道B：A股（通达信等效快扫）

脚本入口：`scripts/screening/a_share_screener.py`
执行方式：Agent 按脚本中定义的 MCP 调用序列依次执行 tdx_quotes → tdx_kline → 排雷清单

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

## 通道C：港股（通达信 target=1）

脚本入口：`scripts/screening/hk_screener.py`
和A股流程相同，但 `target=1` + 阈值放宽（港股无涨跌停板、T+0）：

| 信号 | A股阈值 | 港股阈值 | 放宽原因 |
|------|---------|---------|---------|
| 近N日涨幅 | 15% | 20% | 无涨跌停板限制 |
| 换手率 | 10% | 15% | T+0交易 |
| 20日振幅 | 30% | 40% | 无涨跌停板限制 |
| 市值门槛 | 50亿 | 100亿HKD | 仙股多、机构不碰小票 |

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

`analyze_stock.py` 基于 Yahoo Finance (yfinance)，硬编码美股 ticker 格式。

**不做改造**：A股代码格式（6位数字）与美股 ticker 完全不同；财报是 CSRC 标准而非 SEC EDGAR；A 股无 Short Interest/Put-Call/VIX 等指标。两个通道独立、并行、各管各的市场。

## A股 8维评分的等效映射

stock-analysis 的 8 维量化中，A 股通过 tdx 可等效实现的维度：

| stock-analysis 维度 | A股等效数据源 | 可行性 |
|-------------------|-------------|:--:|
| 盈利（30%） | tdx_indicator_select → ROE/净利率/毛利率 | ✅ |
| 基本面（20%） | tdx_api_data → 三大报表 | ✅ |
| 分析师（20%） | tdx_api_data → 研报评级一致预期 | ✅ |
| 动量（15%） | tdx_kline → 近N日涨跌幅 | ✅ |
| 风险（10%） | tdx_quotes → 振幅/换手率 | ✅ |
| 股息（5%） | tdx_quotes ExtInfo.MGGX | ✅ |
| 情绪（—） | 无等效（VIX/Put-Call 无 A 股对应） | ❌ |
| 内幕（—） | 无等效（SEC EDGAR 无 A 股对应） | ❌ |

完整的市场适配架构文档见 `scripts/screening/README.md`
