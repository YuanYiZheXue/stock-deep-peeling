"""
美股筛选层 —— tdx 直连（已验证，API结构化数据）

2026-06-02 实测：
  - yfinance + 代理：TLS握手超时 ❌
  - WebSearch：通但精度低 🟡
  - **tdx (setcode=74, target=1)：通 ✅ — PE/市值/EPS/股价全量结构化数据**

执行方式：Agent 按 A 股相同流程调用 tdx MCP，使用 setcode=74 + target=1。
脚本位置对标 a_share_screener.py——同一工具，不同市场参数。

美股市场代码：setcode=74（纳斯达克/NYSE通用）
注意：数据延迟15分钟（tdx美国行情标准延迟）
"""

# 美股筛选阈值（与A股相同，无涨跌停板无T+0限制）
PE_HIGH = 50
CHANGE_5D = 0.15
AMPLITUDE_20D = 0.30

def screen_us_stock(ticker: str) -> dict:
    """
    美股筛选层入口（tdx 直连）
    
    执行方式：Agent 调用 tdx MCP 执行以下序列：
    
    Step 1: tdx_lookup_stock(query=ticker, range="MG-GP") → 获取 setcode
    Step 2: tdx_quotes(code, setcode=74, target=1) → PE/市值/换手率/EPS
    Step 3: tdx_kline(code, setcode=74, period=4, wantNum=20, target=1) → 近20日K线
    Step 4: 排雷清单（阈值同A股）
    
    Args:
        ticker: 美股ticker，如 "AAPL"、"TSLA"、"NVDA"
    
    Returns:
        筛选结果dict（与 A 股港股脚本输出格式对齐）
    """
    pass
