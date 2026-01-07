"""
文件input(依赖外部什么): pandas, numpy, scipy.stats, typing, datetime
文件output(提供什么): ICAnalyzer类，提供IC时间序列的全面分析和因子质量评估
文件pos(系统局部地位): 因子研究层，用于评估因子预测能力和稳定性
文件功能:
    1. IC基础统计分析（均值、标准差、ICIR、正IC比例）
    2. 滚动统计分析（窗口统计、趋势检测）
    3. IC稳定性分析（波动率、稳定性评分）
    4. IC分布特征分析（正态性、偏度、峰度、分位数）
    5. 统计显著性检验（t检验、p值、效应量）
    6. 因子失效检测（趋势下降、性能衰退）
    7. 生成综合因子质量评分

使用示例:
    from factors.research.ic_analysis import ICAnalyzer

    # 创建IC分析器
    analyzer = ICAnalyzer(ic_series)

    # 获取基础统计
    stats = analyzer.get_basic_stats()

    # 滚动统计分析
    rolling_stats = analyzer.get_rolling_stats(window=60)

    # 检测下降趋势
    trend = analyzer.detect_decline_trend(window=60)

    # 分析稳定性
    stability = analyzer.analyze_ic_stability()

    # 分析分布特征
    distribution = analyzer.analyze_ic_distribution()

    # 分析显著性
    significance = analyzer.analyze_ic_significance()

    # 生成完整报告
    report = analyzer.generate_ic_analysis_report()

参数说明:
    ic_series: IC时间序列 (pd.Series, index=trade_date)
    window: 滚动窗口大小（默认60天）

返回值:
    Dict[str, float]: 基础统计信息
    pd.DataFrame: 滚动统计数据
    Dict: 趋势分析结果
    Dict: 稳定性指标
    Dict: 分布统计
    Dict: 显著性检验结果
    Dict: 完整分析报告（包含综合评分）
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from scipy import stats
from datetime import datetime


class ICAnalyzer:
    """
    IC时间序列分析器

    功能：
    1. IC统计分析
    2. IC时序趋势分析
    3. IC稳定性分析
    4. 因子失效检测
    """

    def __init__(self, ic_series: pd.Series):
        """
        初始化

        Args:
            ic_series: IC时间序列 [trade_date -> ic_value]
        """
        self.ic_series = ic_series.dropna()

    def get_basic_stats(self) -> Dict[str, float]:
        """获取IC基础统计"""
        if len(self.ic_series) < 2:
            return {}

        return {
            'ic_mean': float(self.ic_series.mean()),
            'ic_std': float(self.ic_series.std()),
            'icir': float(self.ic_series.mean() / self.ic_series.std() if self.ic_series.std() != 0 else 0),
            'ic_min': float(self.ic_series.min()),
            'ic_max': float(self.ic_series.max()),
            'ic_median': float(self.ic_series.median()),
            'positive_ratio': float((self.ic_series > 0).mean()),
            'abs_mean': float(self.ic_series.abs().mean()),
            'count': len(self.ic_series),
        }

    def get_rolling_stats(self, window: int = 60) -> pd.DataFrame:
        """
        计算滚动统计

        Args:
            window: 滚动窗口大小

        Returns:
            pd.DataFrame: 滚动统计数据
        """
        if len(self.ic_series) < window:
            return pd.DataFrame()

        rolling_mean = self.ic_series.rolling(window=window, min_periods=5).mean()
        rolling_std = self.ic_series.rolling(window=window, min_periods=5).std()
        rolling_ir = rolling_mean / rolling_std

        return pd.DataFrame({
            'rolling_mean': rolling_mean,
            'rolling_std': rolling_std,
            'rolling_ir': rolling_ir,
        })

    def detect_decline_trend(self, window: int = 60) -> Dict[str, Any]:
        """
        检测IC下降趋势

        Args:
            window: 分析窗口

        Returns:
            Dict: 趋势分析结果
        """
        if len(self.ic_series) < window * 2:
            return {'has_decline': False, 'reason': '数据不足'}

        # 计算前后半段的统计
        mid_point = len(self.ic_series) // 2
        first_half = self.ic_series.iloc[:mid_point]
        second_half = self.ic_series.iloc[mid_point:]

        first_mean = first_half.mean()
        second_mean = second_half.mean()
        decline_ratio = (second_mean - first_mean) / first_mean if first_mean != 0 else 0

        # 趋势检验
        trend_slope = np.polyfit(range(len(self.ic_series)), self.ic_series.values, 1)[0]

        return {
            'has_decline': decline_ratio < -0.3,  # 下降30%以上认为显著下降
            'first_half_mean': float(first_mean),
            'second_half_mean': float(second_mean),
            'decline_ratio': float(decline_ratio),
            'trend_slope': float(trend_slope),
            'status': '下降' if trend_slope < 0 else '上升或稳定',
        }

    def analyze_ic_stability(self) -> Dict[str, Any]:
        """
        分析IC稳定性

        Returns:
            Dict: 稳定性指标
        """
        if len(self.ic_series) < 10:
            return {'stability_score': 0, 'volatility': 0}

        # 滚动均值稳定性
        rolling_60 = self.ic_series.rolling(window=60, min_periods=10)
        rolling_means = rolling_60.mean().dropna()

        if len(rolling_means) < 2:
            return {'stability_score': 0, 'volatility': 0}

        stability = rolling_means.std()  # 滚动均值的标准差（越小越稳定）
        volatility = self.ic_series.std()  # 波动率

        # 转换为0-100分（越小越稳定）
        stability_score = max(0, min(100, 100 - stability * 100))

        return {
            'stability_score': float(stability_score),
            'volatility': float(volatility),
            'rolling_mean_std': float(stability),
            'is_stable': stability < 0.05,  # 低于0.05认为稳定
        }

    def analyze_ic_distribution(self) -> Dict[str, Any]:
        """
        分析IC分布特征

        Returns:
            Dict: 分布统计
        """
        if len(self.ic_series) < 5:
            return {}

        # 正态性检验
        _, p_value = stats.normaltest(self.ic_series)

        # 偏度和峰度
        skewness = stats.skew(self.ic_series)
        kurtosis = stats.kurtosis(self.ic_series)

        # 分位数
        quantiles = self.ic_series.quantile([0.25, 0.5, 0.75, 0.9, 0.95])

        return {
            'normality_p_value': float(p_value),
            'is_normal': p_value > 0.05,
            'skewness': float(skewness),
            'kurtosis': float(kurtosis),
            'quantiles': quantiles.to_dict(),
            'tails': {
                'extreme_negative': float((self.ic_series < -0.1).mean()),
                'extreme_positive': float((self.ic_series > 0.1).mean()),
            },
        }

    def analyze_ic_significance(self) -> Dict[str, Any]:
        """
        分析IC统计显著性

        Returns:
            Dict: 显著性检验结果
        """
        if len(self.ic_series) < 5:
            return {}

        # t检验：IC均值是否显著不为0
        _, p_value = stats.ttest_1samp(self.ic_series, 0)

        # 计算统计功效（假设有中等效应量0.3）
        effect_size = self.ic_series.mean() / self.ic_series.std() if self.ic_series.std() != 0 else 0

        # 计算达到显著性所需的最少数值
        if p_value < 0.05 and len(self.ic_series) >= 30:
            sig_status = '显著'
        elif p_value < 0.1 and len(self.ic_series) >= 20:
            sig_status = '边际显著'
        else:
            sig_status = '不显著'

        return {
            'p_value': float(p_value),
            'is_significant': p_value < 0.05,
            'effect_size': float(effect_size),
            'significance_status': sig_status,
            'sample_size': len(self.ic_series),
        }

    def generate_ic_analysis_report(self) -> Dict[str, Any]:
        """
        生成完整的IC分析报告

        Returns:
            Dict: 完整分析结果
        """
        report = {
            'basic_stats': self.get_basic_stats(),
            'stability_analysis': self.analyze_ic_stability(),
            'distribution_analysis': self.analyze_ic_distribution(),
            'significance_analysis': self.analyze_ic_significance(),
            'trend_analysis': self.detect_decline_trend(),
        }

        # 综合评分（简化的因子质量评分）
        if len(self.ic_series) >= 30:
            stats = report['basic_stats']
            stability = report['stability_analysis']
            sig = report['significance_analysis']

            # 各维度评分（0-100）
            icir_score = min(abs(stats.get('icir', 0)) * 30, 30)  # ICIR占30分
            stability_score = stability.get('stability_score', 0) * 0.3  # 稳定性占30分
            significance_score = 20 if sig.get('is_significant', False) else 0  # 显著性占20分
            consistency_score = stats.get('positive_ratio', 0) * 20  # 正IC比例占20分

            report['composite_score'] = {
                'total': min(icir_score + stability_score + significance_score + consistency_score, 100),
                'icir_component': icir_score,
                'stability_component': stability_score,
                'significance_component': significance_score,
                'consistency_component': consistency_score,
            }

        return report
