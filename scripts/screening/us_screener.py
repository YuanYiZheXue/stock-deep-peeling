"""
美股筛选层 —— 双通道：yfinance(主) + WebSearch(降级)

调用方式（在 WorkBuddy 上下文中）：
  1. 先检测代理是否可达：HTTP_PROXY=http://127.0.0.1:10809
  2. 代理可达 → 走 yfinance 通道（stock-analysis skill 或直接调用）
  3. 代理不可达 → 降级到 WebSearch 快扫

重要约束：
  - yfinance 直连 Yahoo Finance 被 GFW 拦截，必须走代理
  - WorkBuddy 沙箱默认拦截 localhost 代理端口（10809）
  - 需要用户手动开放沙箱代理白名单，或使用外部可达的代理地址
"""

import os
import subprocess
import json
import sys

PROXY_HOST = "127.0.0.1"
PROXY_PORT = "10809"
PROXY_URL = f"http://{PROXY_HOST}:{PROXY_PORT}"

# 阈值（美股标准，A股不同）
PE_HIGH_THRESHOLD = 50       # 美股PE>50x → ⚠️
CHANGE_5D_THRESHOLD = 0.15   # 近5日涨幅>15% → ⚠️
TURNOVER_THRESHOLD = 0.05    # 美股换手率阈值（比A股低，T+0）

def check_proxy() -> bool:
    """检测代理是否可达"""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((PROXY_HOST, int(PROXY_PORT)))
        s.close()
        return True
    except Exception:
        return False

def screen_via_yfinance(ticker: str) -> dict | None:
    """
    主通道：通过 yfinance + 代理 获取数据
    
    成功条件：
      1. 代理可达
      2. yfinance 已安装
      3. Yahoo Finance API 正常响应
    """
    if not check_proxy():
        return None
    
    os.environ['HTTP_PROXY'] = PROXY_URL
    os.environ['HTTPS_PROXY'] = PROXY_URL
    
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        info = t.info
        
        risk_flags = []
        pe = info.get('trailingPE', 0)
        if pe and pe > PE_HIGH_THRESHOLD:
            risk_flags.append(f"⚠️ PE {pe:.0f}x > {PE_HIGH_THRESHOLD}x")
        elif not pe or pe < 0:
            risk_flags.append("⚫ PE亏损或无法获取")
        
        return {
            "ticker": ticker,
            "market": "US",
            "source": "yfinance",
            "name": info.get('shortName', ticker),
            "price": info.get('currentPrice'),
            "pe_ttm": pe,
            "pe_forward": info.get('forwardPE'),
            "market_cap_usd": info.get('marketCap'),
            "dividend_yield": info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0,
            "risk_flags": risk_flags,
            "pass": "conditional" if len(risk_flags) <= 1 else "warning"
        }
    except Exception as e:
        return None

def screen_via_websearch(ticker: str) -> dict:
    """
    降级通道：通过 WebSearch 获取基础美股数据
    
    数据质量：🟡 精度低于 yfinance，但可作为快速排雷
    覆盖指标：PE(TTM)、市值、最新价、股息率
    不覆盖：8维量化评分（需要 stock-analysis 全量运行）
    """
    # Agent 执行逻辑（非脚本）：
    # 1. WebSearch("<ticker> stock current price PE market cap today")
    # 2. 解析搜索结果中的结构化数据
    # 3. 生产筛选结论
    
    return {
        "ticker": ticker,
        "market": "US",
        "source": "websearch_fallback",
        "note": "代理不可达，降级到WebSearch快扫。精度降低，建议开启代理后重新走yfinance通道。",
        "risk_flags": ["⚠️ 降级模式——缺失8维量化评分"],
        "pass": "conditional"
    }

def screen_us_stock(ticker: str) -> dict:
    """
    美股筛选层入口 —— 自动选择通道
    
    执行路径（Agent在调用本函数时按以下步骤操作）：
      Step 1: check_proxy()
         ├── True → screen_via_yfinance(ticker)
         └── False → screen_via_websearch(ticker)
      Step 2: 输出标准化筛选结论
    
    Args:
        ticker: 美股ticker，如 "AAPL"、"TSLA"、"NVDA"
    
    Returns:
        筛选结果dict（与A股港股脚本输出格式对齐）
    """
    # 优先尝试 yfinance
    result = screen_via_yfinance(ticker)
    if result:
        return result
    
    # 降级到 WebSearch
    return screen_via_websearch(ticker)
