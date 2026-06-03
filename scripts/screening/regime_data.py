# -*- coding: utf-8 -*-
"""
体制检测数据层 —— K线数据转换 + 市场篮子定义

提供从 MCP 原始数据到 regime_detector 输入的标准化转换。
不包含 MCP 调用——MCP 调用由 Agent 在对话中执行。
"""

from __future__ import annotations

import json
from typing import Optional, List, Dict, Tuple
import numpy as np


# ═══════════════════════════════════════════════════════
# 市场篮子定义（全市场适配）
# ═══════════════════════════════════════════════════════

MARKET_BASKETS = {
    # A股
    'sh50': {
        'name': '上证50',
        'market': 'A股',
        'tdx_setcode': '1',
        'screener_msg': '上证50成份股',
        'typical_n': 50,
    },
    'hs300': {
        'name': '沪深300',
        'market': 'A股',
        'tdx_setcode': '1',
        'screener_msg': '沪深300成份股',
        'typical_n': 300,
    },
    'zz500': {
        'name': '中证500',
        'market': 'A股',
        'tdx_setcode': '1',
        'screener_msg': '中证500成份股',
        'typical_n': 500,
    },
    'gem': {
        'name': '创业板指',
        'market': 'A股',
        'tdx_setcode': '0',
        'screener_msg': '创业板指成份股',
        'typical_n': 100,
    },
    'sci_tech': {
        'name': '科创50',
        'market': 'A股',
        'tdx_setcode': '1',
        'screener_msg': '科创50成份股',
        'typical_n': 50,
    },
    # 港股
    'hsi': {
        'name': '恒生指数',
        'market': '港股',
        'tdx_setcode': '31',
        'screener_msg': '恒生指数成份股',
        'typical_n': 82,
    },
    'hstech': {
        'name': '恒生科技',
        'market': '港股',
        'tdx_setcode': '31',
        'screener_msg': '恒生科技成份股',
        'typical_n': 30,
    },
}

def get_basket_info(basket_key: str) -> Optional[dict]:
    """获取篮子定义"""
    return MARKET_BASKETS.get(basket_key)

def list_baskets(market: Optional[str] = None) -> List[Tuple[str, str]]:
    """列出所有篮子 [(key, name), ...]"""
    result = []
    for k, v in MARKET_BASKETS.items():
        if market is None or v['market'] == market:
            result.append((k, v['name']))
    return result


# ═══════════════════════════════════════════════════════
# K线 → 收益率矩阵 转换
# ═══════════════════════════════════════════════════════

def klines_to_returns(
    klines: List[dict],
    window: int = 60,
    price_field: str = 'close',
    use_log: bool = True,
) -> Tuple[np.ndarray, List[str], List[str]]:
    """
    将 K线原始数据转换为收益率矩阵。

    Args:
        klines: K线数据列表，每个元素为:
            {
                'code': str,          # 股票代码
                'name': str,          # 股票名称（可选）
                'close': List[float],  # 收盘价序列（最新在最后）
            }
        window: 取最近 window 个交易日
        price_field: 价格字段名（默认 'close'）
        use_log: 是否使用对数收益率

    Returns:
        returns_matrix: T×N 矩阵 (T=window-1, N=成份股数)
        stock_codes: 代码列表（与矩阵列对应）
        warnings: 警告信息列表

    Example:
        >>> klines = [
        ...     {'code': '600519', 'close': [1780.5, 1788.2, ..., 1795.0]},
        ...     {'code': '000858', 'close': [152.3, 153.1, ..., 151.8]},
        ... ]
        >>> returns, codes, warnings = klines_to_returns(klines, window=60)
        >>> print(f"Matrix shape: {returns.shape}, stocks: {codes}")
    """
    warnings = []

    if not klines:
        return np.array([]), [], ['Empty klines input']

    # 提取每只股票的收盘价序列，对齐长度
    price_arrays = []
    stock_codes = []

    for kline in klines:
        code = kline.get('code', 'unknown')
        prices = kline.get(price_field, [])

        if not prices:
            warnings.append(f'{code}: no price data')
            continue

        # 取最近 window+1 个点（需要一个额外点计算第一个收益率）
        recent = prices[-(window + 1):]

        if len(recent) < 2:
            warnings.append(f'{code}: insufficient data ({len(prices)} total, need >=2)')
            continue

        # 确保是数值类型
        try:
            arr = np.array(recent, dtype=float)
        except (ValueError, TypeError):
            warnings.append(f'{code}: non-numeric prices')
            continue

        price_arrays.append(arr)
        stock_codes.append(code)

    if len(stock_codes) < 3:
        return np.array([]), stock_codes, warnings + ['Total stocks after filtering < 3']

    # 对齐长度（取最短的）
    min_len = min(len(arr) for arr in price_arrays)
    aligned = np.array([arr[-min_len:] for arr in price_arrays])  # N × T_min

    # 计算收益率（转置为 T×N）
    if use_log:
        returns = np.diff(np.log(aligned), axis=1).T  # (T_min-1) × N
    else:
        returns = (np.diff(aligned, axis=1) / aligned[:, :-1]).T

    return returns, stock_codes, warnings


def klines_to_prices(
    klines: List[dict],
    window: int = 60,
    price_field: str = 'close',
) -> Tuple[np.ndarray, List[str], List[str]]:
    """
    与 klines_to_returns 类似，但返回价格矩阵（不计算收益率）。

    用于 regime_detector.compute_from_prices()

    Returns:
        prices_matrix: T×N 矩阵
        stock_codes: 代码列表
        warnings: 警告信息
    """
    warnings = []

    if not klines:
        return np.array([]), [], ['Empty klines input']

    price_arrays = []
    stock_codes = []

    for kline in klines:
        code = kline.get('code', 'unknown')
        prices = kline.get(price_field, [])

        if not prices:
            warnings.append(f'{code}: no price data')
            continue

        recent = prices[-(window + 1):]

        if len(recent) < 2:
            warnings.append(f'{code}: insufficient data')
            continue

        try:
            arr = np.array(recent, dtype=float)
        except (ValueError, TypeError):
            warnings.append(f'{code}: non-numeric prices')
            continue

        price_arrays.append(arr)
        stock_codes.append(code)

    if len(stock_codes) < 3:
        return np.array([]), stock_codes, warnings + ['Total stocks after filtering < 3']

    min_len = min(len(arr) for arr in price_arrays)
    prices = np.array([arr[-min_len:] for arr in price_arrays]).T  # T_min × N

    return prices, stock_codes, warnings


# ═══════════════════════════════════════════════════════
# MCP 桥接（Agent 调用规范）
# ═══════════════════════════════════════════════════════

def mcp_to_regime(
    klines: List[dict],
    window: int = 60,
    basket_label: str = 'custom',
) -> dict:
    """
    Agent 端到端入口：KLines → RegimeResult

    预期调用方式（Agent 侧）：
    1. 用 tdx_screener 获取成份股列表
    2. 逐个/批量用 tdx_kline 获取 K线
    3. 组装为 klines=[{code, close: [...]}, ...]
    4. 执行: python regime_data.py --mcp-to-regime --input klines.json

    Returns:
        dict: RegimeResult.to_dict()
    """
    from regime_detector import RegimeDetector

    returns, codes, warnings = klines_to_returns(klines, window=window)

    if returns.size == 0:
        from regime_detector import RegimeResult
        result = RegimeResult.insufficient(
            reason=f'{basket_label}: no valid returns after processing ({len(klines)} inputs)'
        )
        result.warnings = warnings
        return result.to_dict()

    detector = RegimeDetector()
    result = detector.compute(returns, labels=codes, window=window)
    result.warnings = warnings + result.warnings

    return result.to_dict()


# ═══════════════════════════════════════════════════════
# CLI 入口（Agent 直接调用）
# ═══════════════════════════════════════════════════════

if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--mcp-to-regime':
        # JSON 输入模式：echo '[{code, close:[...]},...]' | python regime_data.py --mcp-to-regime
        try:
            data = json.loads(sys.stdin.read())
        except (json.JSONDecodeError, EOFError) as e:
            print(json.dumps({'error': f'JSON parse failed: {e}'}, ensure_ascii=False))
            sys.exit(1)

        window = int(sys.argv[2]) if len(sys.argv) > 2 else 60
        basket = sys.argv[3] if len(sys.argv) > 3 else 'custom'

        result = mcp_to_regime(data, window=window, basket_label=basket)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif len(sys.argv) > 1 and sys.argv[1] == '--list-baskets':
        market = sys.argv[2] if len(sys.argv) > 2 else None
        baskets = list_baskets(market)
        for k, v in baskets:
            info = MARKET_BASKETS[k]
            print(f"  {k:12s} {v:12s} ({info['market']}, ~{info['typical_n']} constituents)")
    else:
        print("Usage:")
        print("  # 列出所有篮子")
        print("  python regime_data.py --list-baskets [A股|港股]")
        print()
        print("  # 从 K线数据计算体制信号（JSON 管道）")
        print("  cat klines.json | python regime_data.py --mcp-to-regime [window] [basket_label]")
        print()
        print("  # 函数导入")
        print("  from regime_data import klines_to_returns, mcp_to_regime, MARKET_BASKETS")
