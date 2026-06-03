# -*- coding: utf-8 -*-
"""
几何体制检测核心引擎 —— Hammond (2026) arXiv:2605.17117

纯计算模块：输入收益率矩阵 → 输出 RegimeResult
不依赖 MCP/网络/文件IO，仅依赖 numpy。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Tuple, List

import numpy as np


# ═══════════════════════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════════════════════

@dataclass
class RegimeResult:
    """体制检测完整结果"""

    # ── 核心指标 ──
    spectral_entropy: float = 0.0          # 非归一化谱熵: -Σ w_i log(w_i)
    spectral_entropy_normalized: float = 0.0  # 归一化 [0,1], 0=完全集中, 1=完全均匀
    market_purity: float = 0.0             # λ₁ / Σλᵢ, [0,1]

    # ── 辅助指标 ──
    effective_rank: float = 0.0            # exp(S), 独立因子数量
    concentration_ratio_5: float = 0.0     # 前5特征值占比
    condition_number: float = 0.0          # λ_max / λ_min
    eigenvalue_distribution: np.ndarray = field(default_factory=lambda: np.array([]))

    # ── 体制判定 ──
    regime: str = 'unknown'                # 'normal' | 'warning' | 'crisis' | 'insufficient'
    regime_score: float = 0.0              # 0-100, 越高越危险

    # ── 元信息 ──
    n_stocks: int = 0
    window: int = 60
    timestamp: str = ''
    warnings: List[str] = field(default_factory=list)

    @staticmethod
    def insufficient(reason: str) -> 'RegimeResult':
        """数据不足时返回"""
        return RegimeResult(
            regime='insufficient',
            regime_score=0,
            timestamp=datetime.now().isoformat(),
            warnings=[reason],
        )

    def to_dict(self) -> dict:
        """转为可序列化字典（用于 JSON 输出）"""
        return {
            'regime': self.regime,
            'regime_score': round(self.regime_score, 1),
            'spectral_entropy': round(self.spectral_entropy, 3),
            'spectral_entropy_normalized': round(self.spectral_entropy_normalized, 3),
            'market_purity': round(self.market_purity, 3),
            'effective_rank': round(self.effective_rank, 1),
            'concentration_ratio_5': round(self.concentration_ratio_5, 3),
            'condition_number': round(self.condition_number, 1),
            'n_stocks': self.n_stocks,
            'window': self.window,
            'timestamp': self.timestamp,
            'warnings': self.warnings,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    def summary(self) -> str:
        """单行文本摘要"""
        if self.regime == 'insufficient':
            return f"[体制检测] 数据不足: {'; '.join(self.warnings)}"

        emoji = {'normal': '[OK]', 'warning': '[WARN]', 'crisis': '[CRISIS]'}.get(self.regime, '[??]')
        return (
            f"[体制检测] {emoji} {self._regime_label()} "
            f"(谱熵={self.spectral_entropy_normalized:.2f}, "
            f"纯度={self.market_purity:.1%}, "
            f"有效秩={self.effective_rank:.1f}, "
            f"评分={self.regime_score:.0f})"
        )

    def _regime_label(self) -> str:
        return {
            'normal': '正常',
            'warning': '预警',
            'crisis': '危机',
            'insufficient': '数据不足',
        }.get(self.regime, self.regime)

    def __repr__(self) -> str:
        return f"RegimeResult({self.summary()})"


# ═══════════════════════════════════════════════════════
# 核心计算
# ═══════════════════════════════════════════════════════

class RegimeDetector:
    """
    几何体制检测器

    基于相关矩阵的特征值分解，提取体制转换的几何信号。
    参考文献: Hammond, W. (2026), arXiv:2605.17117

    用法:
        >>> detector = RegimeDetector()
        >>> result = detector.compute(returns_matrix)
        >>> print(result.summary())
    """

    # 阈值（Hammond 2026 经验校准 + 实际适配）
    ENTROPY_CRISIS = 0.3       # 低于此 → 危机
    ENTROPY_WARNING = 0.5      # 低于此 → 预警
    PURITY_CRISIS = 0.5        # 高于此 → 危机
    PURITY_WARNING = 0.3       # 高于此 → 预警

    # 数据充足性要求
    MIN_STOCKS = 3              # 最少成份股
    MIN_OBSERVATIONS = 30       # 最少时间窗口

    # 数值稳定性
    RIDGE_ALPHA = 1e-8          # 正则化系数
    ZERO_THRESHOLD = 1e-10      # 零值过滤

    def __init__(
        self,
        entropy_crisis: float = None,
        entropy_warning: float = None,
        purity_crisis: float = None,
        purity_warning: float = None,
    ):
        """允许覆盖阈值（用于不同市场校准）"""
        self.entropy_crisis = entropy_crisis or self.ENTROPY_CRISIS
        self.entropy_warning = entropy_warning or self.ENTROPY_WARNING
        self.purity_crisis = purity_crisis or self.PURITY_CRISIS
        self.purity_warning = purity_warning or self.PURITY_WARNING

    # ── 公开 API ──

    def compute(
        self,
        returns: np.ndarray,
        labels: Optional[List[str]] = None,
        window: int = 60,
    ) -> RegimeResult:
        """
        从收益率矩阵计算体制信号

        Args:
            returns: T×N 矩阵 (T=时间点, N=成份股)，已剔除 NA
            labels: 成份股标签列表（可选）
            window: 时间窗口大小（用于元信息）

        Returns:
            RegimeResult
        """
        warnings = []

        # ── 1. 输入验证 ──
        if returns.ndim != 2:
            return RegimeResult.insufficient(f'Expected 2D array, got {returns.ndim}D')

        T, N = returns.shape
        if N < self.MIN_STOCKS:
            return RegimeResult.insufficient(
                f'Insufficient stocks: {N} < {self.MIN_STOCKS}'
            )

        # ── 2. 数据清洗 ──
        returns, clean_warnings = self._clean_data(returns, labels)
        warnings.extend(clean_warnings)

        T_clean, N_clean = returns.shape
        if T_clean < self.MIN_OBSERVATIONS:
            return RegimeResult.insufficient(
                f'Insufficient observations: {T_clean} < {self.MIN_OBSERVATIONS}'
            )
        if N_clean < self.MIN_STOCKS:
            return RegimeResult.insufficient(
                f'After cleaning: {N_clean} stocks < {self.MIN_STOCKS}'
            )

        # ── 3. 计算相关矩阵（带正则化） ──
        corr = np.corrcoef(returns.T)
        # 正则化：对奇异矩阵添加小幅扰动
        corr_regularized = corr + self.RIDGE_ALPHA * np.eye(N_clean)

        # ── 4. 特征值分解 ──
        try:
            eigvals = np.linalg.eigvalsh(corr_regularized)
        except np.linalg.LinAlgError:
            # 回退：使用pinv
            try:
                eigvals = np.linalg.eigvalsh(np.linalg.pinv(corr))
            except np.linalg.LinAlgError:
                return RegimeResult.insufficient('Eigenvalue decomposition failed')

        # 排序（升序 → 降序）
        eigvals = eigvals[::-1]
        # 过滤浮点精度产生的负值
        eigvals = np.maximum(eigvals, 0)
        total = eigvals.sum()
        if total < self.ZERO_THRESHOLD:
            return RegimeResult.insufficient('All eigenvalues near zero')

        # ── 5. 计算指标 ──
        weights = eigvals / total  # w_i

        # Spectral Entropy
        valid_w = weights[weights > self.ZERO_THRESHOLD]
        spectral_entropy = -np.sum(valid_w * np.log(valid_w))
        max_entropy = np.log(N_clean)
        entropy_normalized = spectral_entropy / max_entropy if max_entropy > 0 else 0

        # Market Purity
        market_purity = weights[0]  # λ₁ / Σλᵢ

        # Effective Rank
        effective_rank = np.exp(spectral_entropy) if spectral_entropy > 0 else 0

        # Concentration Ratio (top 5)
        top5 = min(5, N_clean)
        concentration_ratio_5 = weights[:top5].sum()

        # Condition Number
        if eigvals[-1] > self.ZERO_THRESHOLD:
            condition_number = eigvals[0] / eigvals[-1]
        else:
            condition_number = float('inf')
            warnings.append('min eigenvalue near zero, condition_number=inf')

        # ── 6. 体制判定 ──
        regime, regime_score = self._classify_regime(entropy_normalized, market_purity)

        return RegimeResult(
            spectral_entropy=spectral_entropy,
            spectral_entropy_normalized=entropy_normalized,
            market_purity=market_purity,
            effective_rank=effective_rank,
            concentration_ratio_5=concentration_ratio_5,
            condition_number=condition_number,
            eigenvalue_distribution=eigvals,
            regime=regime,
            regime_score=regime_score,
            n_stocks=N_clean,
            window=window,
            timestamp=datetime.now().isoformat(),
            warnings=warnings,
        )

    def compute_from_prices(
        self,
        prices: np.ndarray,
        window: int = 60,
    ) -> RegimeResult:
        """
        从价格矩阵计算体制信号（自动转对数收益率）

        Args:
            prices: (T+1)×N 矩阵，每列是一只股票的价格序列
            window: 时间窗口

        Returns:
            RegimeResult
        """
        if prices.ndim != 2 or prices.shape[0] < 2:
            return RegimeResult.insufficient('Need at least 2 price points')

        # 对数收益率
        returns = np.diff(np.log(prices), axis=0)

        # 取最近 window 个交易日
        if returns.shape[0] > window:
            returns = returns[-window:]

        return self.compute(returns, window=window)

    # ── 内部方法 ──

    def _clean_data(
        self,
        returns: np.ndarray,
        labels: Optional[List[str]] = None,
    ) -> Tuple[np.ndarray, List[str]]:
        """清洗收益率矩阵"""
        warnings = []
        N = returns.shape[1]

        # 1. 剔除全 NaN 列
        nan_mask = np.all(np.isnan(returns), axis=0)
        if nan_mask.any():
            n_dropped = nan_mask.sum()
            dropped_names = (
                [labels[i] for i, m in enumerate(nan_mask) if m]
                if labels else []
            )
            warnings.append(
                f'Dropped {n_dropped} stocks with all-NaN: {dropped_names[:5]}'
                + ('...' if n_dropped > 5 else '')
            )
            returns = returns[:, ~nan_mask]

        # 2. 剔除方差为 0 的列（价格完全不变）
        var = np.nanvar(returns, axis=0)
        zero_var_mask = var < self.ZERO_THRESHOLD
        if zero_var_mask.any():
            warnings.append(f'Dropped {zero_var_mask.sum()} stocks with zero variance')
            returns = returns[:, ~zero_var_mask]

        # 3. 对剩余 NaN 用列均值填充
        col_means = np.nanmean(returns, axis=0)
        nan_indices = np.where(np.isnan(returns))
        if len(nan_indices[0]) > 0:
            for j in np.unique(nan_indices[1]):
                col_nans = np.isnan(returns[:, j])
                returns[col_nans, j] = col_means[j]
            warnings.append(f'Filled NaN with column means ({len(nan_indices[0])} cells)')

        return returns, warnings

    def _classify_regime(self, entropy_norm: float, purity: float) -> Tuple[str, float]:
        """双因子体制判定"""
        # 危机信号（任一触发）
        if entropy_norm < self.entropy_crisis or purity > self.purity_crisis:
            return 'crisis', self._calc_score(entropy_norm, purity, 'crisis')

        # 预警信号（任一触发）
        if entropy_norm < self.entropy_warning or purity > self.purity_warning:
            return 'warning', self._calc_score(entropy_norm, purity, 'warning')

        return 'normal', self._calc_score(entropy_norm, purity, 'normal')

    def _calc_score(self, entropy_norm: float, purity: float, base_regime: str) -> float:
        """计算 0-100 的综合风险评分"""
        # 熵越低越危险，纯度越高越危险
        entropy_risk = (1 - entropy_norm) * 50   # [0, 50]
        purity_risk = purity * 50                 # [0, 50]

        # 基础偏移（体制加权）
        base_offset = {'normal': 0, 'warning': 20, 'crisis': 40}[base_regime]
        score = min(100, entropy_risk + purity_risk + base_offset)
        return round(score, 1)


# ═══════════════════════════════════════════════════════
# 便捷函数（无需实例化）
# ═══════════════════════════════════════════════════════

_default_detector = RegimeDetector()

def detect_regime(returns: np.ndarray, window: int = 60) -> RegimeResult:
    """便捷入口：直接检测"""
    return _default_detector.compute(returns, window=window)

def detect_regime_from_prices(prices: np.ndarray, window: int = 60) -> RegimeResult:
    """便捷入口：从价格检测"""
    return _default_detector.compute_from_prices(prices, window=window)


# ═══════════════════════════════════════════════════════
# 自测（内部验证）
# ═══════════════════════════════════════════════════════

if __name__ == '__main__':
    np.random.seed(42)
    detector = RegimeDetector()
    n_stocks, n_days = 10, 60

    def run_test(name: str, corr_strength: float) -> dict:
        """生成指定相关强度的收益率矩阵并检测"""
        # 构造相关矩阵: 对角线1, 非对角线=corr_strength
        cov = corr_strength * np.ones((n_stocks, n_stocks)) + (1 - corr_strength) * np.eye(n_stocks)
        L = np.linalg.cholesky(cov)
        returns = L @ np.random.randn(n_stocks, n_days)
        result = detector.compute(returns.T)
        print(f"\n{'='*50}")
        print(f"  {name} (ρ={corr_strength})")
        print(f"  {result.summary()}")
        return result.to_dict()

    # 测试1: 完全独立 → 正常
    run_test("完全独立", 0.0)
    # 测试2: 弱相关 → 正常
    run_test("弱相关", 0.2)
    # 测试3: 中等相关 → 预警
    run_test("中等相关", 0.5)
    # 测试4: 强相关 → 危机
    run_test("强相关", 0.85)
    # 测试5: 完全一致 → 危机
    run_test("完全一致", 0.99)

    # 边界测试: 成份股不足
    print("\n" + "="*50)
    print("  边界: 2只股票")
    result = detector.compute(np.random.randn(60, 2))
    print(f"  {result.summary()}")

    # 边界测试: NaN 处理
    print("\n" + "="*50)
    print("  边界: NaN 处理")
    data = np.random.randn(60, 10)
    data[:10, 0] = np.nan  # 前10行第一列为NaN
    data[:, 1] = np.nan     # 整个第二列为NaN
    result = detector.compute(data)
    print(f"  {result.summary()}")
    print(f"  Warnings: {result.warnings}")

    print("\n*** Self-test complete ***")
