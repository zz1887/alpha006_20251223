"""
文件input(依赖外部什么): pandas, numpy, scipy.stats, typing, itertools
文件output(提供什么): FactorDiscovery类，提供因子发现、变换、组合探索和有效性筛选
文件pos(系统局部地位): 因子研究层，用于系统化发现和验证新的有效因子
文件功能:
    1. 基础因子变换（对数、秩、Z-score、滞后、差分）
    2. 算术组合探索（加减乘除、多因子组合）
    3. 滞后组合因子（多期滞后、滚动均值）
    4. 因子有效性评估（IC/ICIR/分组收益/换手率/综合评分）
    5. 因子筛选（按有效性排序选取最优因子）
    6. 时间稳定性分析（分段ICIR、稳定性评分）
    7. 生成完整因子发现报告

使用示例:
    from factors.research.discovery import FactorDiscovery

    # 生成基础变换因子
    transformed = FactorDiscovery.generate_basic_transformations(
        base_df, 'pe_ttm', ['log', 'rank', 'zscore']
    )

    # 探索算术组合
    combinations = FactorDiscovery.explore_arithmetic_combinations(
        base_df, ['factor1', 'factor2'], max_complexity=2
    )

    # 生成滞后组合
    lag_combined = FactorDiscovery.generate_lag_combinations(
        base_df, 'momentum_factor', lags=[1, 2, 3, 5, 10]
    )

    # 计算因子有效性
    effectiveness = FactorDiscovery.calculate_factor_effectiveness(
        factor_df, forward_returns
    )

    # 因子筛选
    top_factors = FactorDiscovery.screen_factors(
        factor_data, forward_returns, ['f1', 'f2', 'f3'], top_n=5
    )

    # 时间稳定性分析
    stability = FactorDiscovery.analyze_factor_stability_over_time(
        factor_df, forward_returns, n_periods=5
    )

    # 生成发现报告
    report = FactorDiscovery.generate_discovery_report(
        'new_factor', factor_df, forward_returns
    )

参数说明:
    base_df: 基础数据 [ts_code, trade_date, ...]
    factor_col: 因子列名
    factor_cols: 因子列名列表
    factor_df: 因子数据 [ts_code, trade_date, factor]
    factor_data: 包含多个因子的数据
    forward_returns: 前瞻收益率 [ts_code, trade_date, forward_return]
    transformations: 变换类型列表
    max_complexity: 最大组合复杂度
    lags: 滞后期数列表
    min_periods: 最小样本数
    top_n: 选取前N个
    n_periods: 分段数

返回值:
    pd.DataFrame: 包含变换/组合因子的数据
    Dict: 有效性评估结果
    List[Tuple]: 筛选后的因子 [(因子名, 得分), ...]
    Dict: 稳定性分析结果
    Dict: 完整发现报告
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from scipy import stats
from itertools import combinations


class FactorDiscovery:
    """
    因子发现器

    功能：
    1. 基础因子生成
    2. 因子组合探索
    3. 因子有效性筛选
    4. 因子特征分析
    """

    @staticmethod
    def generate_basic_transformations(base_df: pd.DataFrame,
                                     factor_col: str,
                                     transformations: List[str] = None) -> pd.DataFrame:
        """
        生成基础变换因子

        Args:
            base_df: 基础数据 [ts_code, trade_date, ...]
            factor_col: 基础因子列名
            transformations: 变换类型列表

        Returns:
            pd.DataFrame: 包含变换因子的数据
        """
        if transformations is None:
            transformations = ['log', 'rank', 'zscore', 'delay', 'diff']

        result = base_df.copy()

        for trans in transformations:
            if trans == 'log':
                # 对数变换（处理正数）
                result[f'{factor_col}_log'] = np.log(result[factor_col].clip(lower=1e-6))

            elif trans == 'rank':
                # 秩变换（标准化到0-1）
                result[f'{factor_col}_rank'] = result.groupby('trade_date')[factor_col].rank(pct=True)

            elif trans == 'zscore':
                # Z-score标准化
                result[f'{factor_col}_zscore'] = result.groupby('trade_date')[factor_col].transform(
                    lambda x: (x - x.mean()) / x.std() if x.std() != 0 else 0
                )

            elif trans == 'delay':
                # 滞后一期
                result[f'{factor_col}_delay'] = result.groupby('ts_code')[factor_col].shift(1)

            elif trans == 'diff':
                # 差分
                result[f'{factor_col}_diff'] = result.groupby('ts_code')[factor_col].diff()

        return result

    @staticmethod
    def explore_arithmetic_combinations(base_df: pd.DataFrame,
                                       factor_cols: List[str],
                                       max_complexity: int = 2) -> pd.DataFrame:
        """
        探索算术组合因子

        Args:
            base_df: 基础数据
            factor_cols: 基础因子列名列表
            max_complexity: 最大组合复杂度

        Returns:
            pd.DataFrame: 包含组合因子的数据
        """
        result = base_df.copy()

        # 两两组合
        if max_complexity >= 2:
            for f1, f2 in combinations(factor_cols, 2):
                # 加法
                result[f'{f1}_plus_{f2}'] = result[f1] + result[f2]
                # 减法
                result[f'{f1}_minus_{f2}'] = result[f1] - result[f2]
                # 乘法
                result[f'{f1}_times_{f2}'] = result[f1] * result[f2]
                # 除法（避免除零）
                result[f'{f1}_div_{f2}'] = result[f1] / result[f2].replace(0, np.nan)

        # 三三组合（可选，计算量大）
        if max_complexity >= 3:
            for f1, f2, f3 in combinations(factor_cols, 3):
                result[f'{f1}_plus_{f2}_plus_{f3}'] = result[f1] + result[f2] + result[f3]
                result[f'{f1}_times_{f2}_times_{f3}'] = result[f1] * result[f2] * result[f3]

        return result

    @staticmethod
    def generate_lag_combinations(base_df: pd.DataFrame,
                                 factor_col: str,
                                 lags: List[int] = None) -> pd.DataFrame:
        """
        生成滞后组合因子

        Args:
            base_df: 基础数据
            factor_col: 因子列名
            lags: 滞后期数列表

        Returns:
            pd.DataFrame: 包含滞后因子的数据
        """
        if lags is None:
            lags = [1, 2, 3, 5, 10]

        result = base_df.copy()

        for lag in lags:
            result[f'{factor_col}_lag{lag}'] = result.groupby('ts_code')[factor_col].shift(lag)

        # 滞后均值
        for lag in [5, 10, 20]:
            result[f'{factor_col}_mean{lag}'] = result.groupby('ts_code')[factor_col].rolling(
                window=lag, min_periods=1
            ).mean().reset_index(level=0, drop=True)

        return result

    @staticmethod
    def calculate_factor_effectiveness(factor_df: pd.DataFrame,
                                      forward_returns: pd.DataFrame,
                                      min_periods: int = 30) -> Dict[str, Any]:
        """
        计算因子有效性指标

        Args:
            factor_df: 因子数据
            forward_returns: 前瞻收益率
            min_periods: 最小样本数

        Returns:
            Dict: 有效性评估结果
        """
        from .metrics import FactorMetrics

        # 计算IC
        ic_series = FactorMetrics.calculate_ic(factor_df, forward_returns)

        if len(ic_series) < min_periods:
            return {
                'is_valid': False,
                'reason': 'IC样本不足',
                'ic_count': len(ic_series),
            }

        # 计算ICIR
        icir_stats = FactorMetrics.calculate_icir(ic_series)

        # 计算分组收益
        group_stats = FactorMetrics.calculate_group_returns(factor_df, forward_returns, n_groups=5)

        # 计算换手率
        turnover = FactorMetrics.calculate_turnover(factor_df)

        # 综合评分
        score = 0
        icir = icir_stats.get('icir', 0)
        score += min(abs(icir) * 40, 40)  # ICIR占40分

        if 'group_1_vs_5' in group_stats:
            score += min(group_stats['group_1_vs_5'] * 100, 30)  # 分组差异占30分

        score += max(0, (1 - turnover) * 30)  # 换手率占30分

        return {
            'is_valid': score >= 30 and abs(icir) >= 0.05,
            'score': score,
            'icir': icir,
            'ic_mean': icir_stats.get('ic_mean', 0),
            'group_diff': group_stats.get('group_1_vs_5', 0),
            'turnover': turnover,
            'ic_count': len(ic_series),
            'status': '有效' if score >= 30 else '无效',
        }

    @staticmethod
    def screen_factors(factor_data: pd.DataFrame,
                      forward_returns: pd.DataFrame,
                      factor_cols: List[str],
                      top_n: int = 10) -> List[Tuple[str, float]]:
        """
        因子筛选（按有效性排序）

        Args:
            factor_data: 包含多个因子的数据
            forward_returns: 前瞻收益率
            factor_cols: 待筛选的因子列名
            top_n: 选取前N个

        Returns:
            List: [(因子名, 得分), ...]
        """
        factor_scores = []

        for col in factor_cols:
            if col not in factor_data.columns:
                continue

            # 构造单因子数据
            factor_df = factor_data[['ts_code', 'trade_date', col]].copy()
            factor_df = factor_df.rename(columns={col: 'factor'})

            # 计算有效性
            effectiveness = FactorDiscovery.calculate_factor_effectiveness(
                factor_df, forward_returns
            )

            if effectiveness['is_valid']:
                factor_scores.append((col, effectiveness['score']))

        # 按得分排序
        factor_scores.sort(key=lambda x: x[1], reverse=True)

        return factor_scores[:top_n]

    @staticmethod
    def analyze_factor_stability_over_time(factor_df: pd.DataFrame,
                                          forward_returns: pd.DataFrame,
                                          n_periods: int = 5) -> Dict[str, Any]:
        """
        分析因子在时间上的稳定性

        Args:
            factor_df: 因子数据
            forward_returns: 前瞻收益率
            n_periods: 分段数

        Returns:
            Dict: 稳定性分析结果
        """
        from .metrics import FactorMetrics

        # 按时间分段
        dates = factor_df['trade_date'].sort_values().unique()
        period_size = len(dates) // n_periods

        period_icirs = []
        period_scores = []

        for i in range(n_periods):
            start_idx = i * period_size
            end_idx = (i + 1) * period_size if i < n_periods - 1 else len(dates)

            period_dates = dates[start_idx:end_idx]

            period_factor = factor_df[factor_df['trade_date'].isin(period_dates)]
            period_returns = forward_returns[forward_returns['trade_date'].isin(period_dates)]

            if len(period_factor) == 0 or len(period_returns) == 0:
                continue

            # 计算该时段的ICIR
            ic_series = FactorMetrics.calculate_ic(period_factor, period_returns)
            if len(ic_series) > 1:
                icir = ic_series.mean() / ic_series.std() if ic_series.std() != 0 else 0
                period_icirs.append(icir)

                # 计算该时段得分
                group_stats = FactorMetrics.calculate_group_returns(period_factor, period_returns)
                turnover = FactorMetrics.calculate_turnover(period_factor)

                score = min(abs(icir) * 40, 40)
                if 'group_1_vs_5' in group_stats:
                    score += min(group_stats['group_1_vs_5'] * 100, 30)
                score += max(0, (1 - turnover) * 30)
                period_scores.append(score)

        if not period_icirs:
            return {'error': '数据不足'}

        # 计算稳定性
        icir_std = np.std(period_icirs)
        icir_mean = np.mean(period_icirs)
        stability_score = max(0, 100 - icir_std * 100)

        return {
            'period_icirs': period_icirs,
            'period_scores': period_scores,
            'icir_mean': icir_mean,
            'icir_std': icir_std,
            'stability_score': stability_score,
            'is_stable': stability_score > 70,
            'trend': '稳定' if icir_std < 0.1 else '波动较大',
        }

    @staticmethod
    def generate_discovery_report(factor_name: str,
                                 factor_df: pd.DataFrame,
                                 forward_returns: pd.DataFrame,
                                 base_metrics: Optional[Dict] = None) -> Dict[str, Any]:
        """
        生成因子发现报告

        Args:
            factor_name: 因子名称
            factor_df: 因子数据
            forward_returns: 前瞻收益率
            base_metrics: 基础指标（可选）

        Returns:
            Dict: 完整发现报告
        """
        from .metrics import FactorMetrics

        # 基础统计
        factor_col = [c for c in factor_df.columns if c not in ['ts_code', 'trade_date']][0]
        valid_data = factor_df[factor_col].dropna()

        basic_stats = {
            'total_records': len(factor_df),
            'valid_records': len(valid_data),
            'missing_ratio': 1 - len(valid_data) / len(factor_df),
            'stock_count': factor_df['ts_code'].nunique(),
            'date_count': factor_df['trade_date'].nunique(),
            'mean': float(valid_data.mean()),
            'std': float(valid_data.std()),
            'min': float(valid_data.min()),
            'max': float(valid_data.max()),
        }

        # 有效性评估
        effectiveness = FactorDiscovery.calculate_factor_effectiveness(
            factor_df, forward_returns
        )

        # IC分析
        ic_series = FactorMetrics.calculate_ic(factor_df, forward_returns)
        icir_stats = FactorMetrics.calculate_icir(ic_series)

        # 分组分析
        group_stats = FactorMetrics.calculate_group_returns(factor_df, forward_returns)

        # 稳定性分析
        stability = FactorDiscovery.analyze_factor_stability_over_time(
            factor_df, forward_returns
        )

        # 综合评估
        report = {
            'factor_name': factor_name,
            'basic_stats': basic_stats,
            'effectiveness': effectiveness,
            'ic_analysis': icir_stats,
            'group_analysis': group_stats,
            'stability_analysis': stability,
            'recommendation': FactorDiscovery._generate_recommendation(effectiveness, stability),
        }

        return report

    @staticmethod
    def _generate_recommendation(effectiveness: Dict, stability: Dict) -> str:
        """
        生成因子改进建议

        Args:
            effectiveness: 有效性指标
            stability: 稳定性指标

        Returns:
            str: 建议文本
        """
        if not effectiveness['is_valid']:
            return "因子无效，建议重新设计或尝试变换"

        if isinstance(stability, dict) and stability.get('is_stable', False):
            return "因子有效且稳定，建议直接使用"
        elif isinstance(stability, dict) and not stability.get('is_stable', False):
            return "因子有效但不稳定，建议增加行业中性化或参数优化"
        else:
            return "因子有效，建议进一步验证稳定性"
