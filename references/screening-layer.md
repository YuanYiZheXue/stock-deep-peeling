# 筛选层 —— 量化快扫 + 信号探测

> 本层调用外部 skill `stock-analysis`，在执行九步深层穿透之前完成量化筛选和信号探测。
> 不替代穿透层——只做"该不该继续看"的判断。

## 调用方式

加载 `stock-analysis` skill 后，使用以下命令：

```bash
# 快速量化扫描（--fast 跳过内幕交易+新闻，2-3秒）
uv run {baseDir}/scripts/analyze_stock.py <ticker> --fast

# 多标的对比
uv run {baseDir}/scripts/analyze_stock.py <ticker1> <ticker2> --fast

# 传闻/内幕扫描（M&A信号、分析师变动、Twitter传闻）
python3 {baseDir}/scripts/rumor_scanner.py

# 热力扫描（发现趋势标的）
python3 {baseDir}/scripts/hot_scanner.py
```

## 筛选层输出

完成筛选后，输出以下表格决定是否进入穿透层：

| 指标 | 来源 | 阈值 | 通过条件 |
|------|------|------|---------|
| 综合评分 | 8维量化 | 0-100 | ≥60 → 通过 |
| 风险标记 | 风险检测 | 0-5个 | ≤2 → 通过 |
| 传闻信号 | Rumor Scanner | M&A/内幕/分析师 | 有→记录，不影响通过 |
| 股息安全 | Dividend | 0-100 | 仅分红标的参考 |

## 仅适用美股

`stock-analysis` 基于 Yahoo Finance，仅覆盖美股和加密货币。
A股/港股标的**跳过筛选层，直接进穿透层**。

## 快速排雷（A股补充）

A股不能调 stock-analysis，使用通达信 `tdx_quotes` + `tdx_kline` 做等效快扫：

```bash
# PE/市值/换手率
tdx_quotes code="688206" setcode="1"

# 近20日K线（判断是否异常波动）
tdx_kline code="688206" setcode="1" period="4" wantNum="20"
```

排雷清单：
- PE > 100x 且利润萎缩 → ⚫ 标志
- 近5日涨幅 > 15% → ⚠️ 追高风险
- 换手率 > 10% → ⚠️ 游资炒作
- 股息率 = 0 → 不意外，但记录

## 筛选结论模板

```
【筛选层结论】
标的：<名称/代码>
数据源：stock-analysis(美股) / tdx( A股)
量化评分：XX/100
风险标记：X个（列举）
传闻/异常：有/无（列举）
筛选结论：✅进入穿透层 / ⚠️有条件进入 / ❌跳过
```
