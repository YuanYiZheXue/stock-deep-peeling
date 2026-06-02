"""
A股筛选层快扫脚本

调用方式（在 WorkBuddy 技能上下文中）：
  加载 stock-deep-peeling skill → 判断代码为A股 → 执行本脚本

等价于以下 MCP 调用序列：
  1. mcp__tdx-connector__tdx_quotes(code, setcode) → PE/市值/换手率
  2. mcp__tdx-connector__tdx_kline(code, setcode, period=4, wantNum=20) → 近20日K线
  3. 排雷清单逐项检查

输出格式（与 stock-analysis 的 us_analyze_stock.py 对齐）：
{
  "ticker": "688206",
  "market": "A",
  "name": "概伦电子",
  "price": 36.20,
  "pe_ttm": -321.4,
  "market_cap_cny": 15800000000,
  "turnover_rate": 2.05,
  "change_5d_pct": -19.6,
  "amplitude_20d_pct": 40.6,
  "dividend_yield": 0.22,
  "risk_flags": ["PE亏损", "振幅>30%", "股息0+PE>50x"],
  "pass": "conditional",
  "pass_reason": "PE亏损、近期公告驱动游资拉高出货"
}

排雷阈值（可调参）：
  PE_LOSS_THRESHOLD = True          # PE为负(亏损) → ⚫
  PE_HIGH_THRESHOLD = 100           # PE > 100x + 利润下滑 → ⚫
  CHANGE_5D_THRESHOLD = 0.15        # 近5日涨幅 > 15% → ⚠️
  TURNOVER_THRESHOLD = 0.10         # 换手率 > 10% → ⚠️
  AMPLITUDE_20D_THRESHOLD = 0.30    # 20日振幅 > 30% → ⚠️
  DIVIDEND_ZERO_PE_HIGH = True      # 股息=0 且 PE>50x → ⚠️
  MCAP_SMALL_THRESHOLD = 50亿       # 市值<50亿 → ⚠️
"""

# 以下为脚本模板——在 WorkBuddy 环境中由 Agent 调用 MCP 执行
# 此处仅作接口文档，实际执行由 Agent 按上述 MCP 调用序列完成

def screen_a_share(code: str, setcode: str = "1") -> dict:
    """
    A股筛选层入口
    
    Args:
        code: 6位股票代码，如 "688206"
        setcode: 市场代码，"1"=沪市，"0"=深市，"2"=北交所
    
    Returns:
        筛选结果dict，格式见上方输出规范
    """
    # Step 1: 实时行情
    # quotes = mcp__tdx-connector__tdx_quotes(code, setcode)
    
    # Step 2: 近20日K线
    # kline = mcp__tdx-connector__tdx_kline(code, setcode, period=4, wantNum=20)
    
    # Step 3: 排雷清单
    # flags = run_risk_checklist(quotes, kline)
    
    # Step 4: 输出
    # return format_output(quotes, kline, flags)
    pass


def run_risk_checklist(quotes: dict, kline: dict) -> list:
    """六项排雷逐项检查"""
    flags = []
    
    # 1. PE亏损或超高
    # pe = quotes.ExtInfo.SYL
    # if pe < 0 or (pe > 100 and is_profit_declining(kline)):
    #     flags.append("⚫ PE亏损或>100x且利润萎缩")
    
    # 2. 近5日涨幅
    # change_5d = calc_change(kline, 5)
    # if change_5d > 0.15:
    #     flags.append(f"⚠️ 近5日涨幅 {change_5d:.1%}>15%")
    
    # 3. 换手率
    # hsl = quotes.HQInfo.HSL
    # if hsl > 10:
    #     flags.append(f"⚠️ 换手率 {hsl:.1f}%>10%")
    
    # 4. 20日振幅
    # amp = calc_amplitude(kline)
    # if amp > 0.30:
    #     flags.append(f"⚠️ 20日振幅 {amp:.1%}>30%")
    
    # 5. 股息检查
    # div = quotes.ExtInfo.MGGX
    # if div == 0 and pe > 50:
    #     flags.append("⚠️ 股息=0且PE>50x")
    
    # 6. 市值
    # mcap = quotes.ExtInfo.ZSZ
    # if mcap < 50_0000_0000:
    #     flags.append("⚠️ 市值<50亿")
    
    return flags
