"""
文件input(依赖外部什么): pandas, numpy, scipy.stats
文件output(提供什么): FactorMetrics类，提供因子评价指标计算
文件pos(系统局部地位): 因子评估核心模块，计算IC/ICIR/分组收益/换手率等关键指标
文件功能:
    1. 信息系数(IC)计算
    2. 信息比率(ICIR)计算
    3. 因子收益率计算
    4. 分组回测收益计算
    5. 换手率计算
    6. 因子稳定性计算

使用示例:
    from factors.evaluation.metrics import FactorMetrics

    # 计算IC
    ic_series = FactorMetrics.calculate_ic(factor_df, forward_returns)

    # 计算ICIR
    icir = FactorMetrics.calculate_icir(ic_series)

    # 分组回测
    group_returns = FactorMetrics.calculate_group_returns(
        factor_df, forward_returns, n_groups=5
    )

参数说明:
    factor_df: 因子数据 [ts_code, trade_date, factor]
    forward_returns: 前瞻收益率 [ts_code, trade_date, forward_return]
    method: 相关系数方法 ('spearman' or 'pearson')
    n_groups: 分组数量 (默认5)

返回值:
    pd.Series: IC时间序列
    float: ICIR值
    pd.DataFrame: 分组收益率
    float: 换手率
    Dict[str, float]: 稳定性指标
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple
from scipy.stats import spearmanr


class FactorMetrics:
    """
    因子评价指标计算类

    提供以下指标计算：
    - IC (信息系数)
    - ICIR (信息比率)
    - 因子收益率
    - 分组回测收益
    - 换手率
    - 因子稳定性
    """

    @staticmethod
    def calculate_ic(factor_df: pd.DataFrame,
                    forward_returns: pd.DataFrame,
                    method: str = 'spearman') -> pd.Series:
        """
        计算信息系数(IC)

        Args:
            factor_df: 因子数据 [ts_code, trade_date, factor]
            forward_returns: 前瞻收益率 [ts_code, trade_date, forward_return]
            method: 相关系数方法 ('spearman' or 'pearson')

        Returns:
            pd.Series: 每日IC值
        """
        # 合并数据
        merged = pd.merge(
            factor_df, forward_returns,
            on=['ts_code', 'trade_date'],
            how='inner'
        )

        if len(merged) == 0:
            return pd.Series(dtype=float)

        # 计算每日IC
        def calc_daily_ic(group):
            if len(group) < 3:
                return np.nan

            factor_values = group['factor'].values
            forward_rets = group['forward_return'].values

            if method == 'spearman':
                corr, _ = spearmanr(factor_values, forward_rets)
            else:
                corr = np.corrcoef(factor_values, forward_rets)[0, 1]

            return corr

        ic_series = merged.groupby('trade_date').apply(calc_daily_ic)

        return ic_series.dropna()

    @staticmethod
    def calculate_icir(ic_series: pd.Series) -> Dict[str, float]:
        """
        计算ICIR及相关统计

        Args:
            ic_series: IC时间序列

        Returns:
            Dict[str, float]: ICIR统计字典
        """
        if len(ic_series) < 2:
            return {'ic_mean': 0.0, 'ic_std': 0.0, 'icir': 0.0}

        ic_mean = ic_series.mean()
        ic_std = ic_series.std()

        if ic_std == 0:
            icir = 0.0
        else:
            icir = ic_mean / ic_std

        return {
            'ic_mean': float(ic_mean),
            'ic_std': float(ic_std),
            'icir': float(icir),
            'ic_positive_ratio': float((ic_series > 0).mean()),
            'ic_abs_mean': float(ic_series.abs().mean()),
        }

    @staticmethod
    def calculate_factor_return(factor_df: pd.DataFrame,
                               forward_returns: pd.DataFrame,
                               method: str = 'ols') -> pd.DataFrame:
        """
        计算因子收益率

        Args:
            factor_df: 因子数据
            forward_returns: 前瞻收益率
            method: 计算方法 ('ols' or 'weighted')

        Returns:
            pd.DataFrame: 每日因子收益率
        """
        merged = pd.merge(
            factor_df, forward_returns,
            on=['ts_code', 'trade_date'],
            how='inner'
        )

        if len(merged) == 0:
            return pd.DataFrame()

        def calc_daily_return(group):
            if len(group) < 3:
                return np.nan

            factor = group['factor'].values
            ret = group['forward_return'].values

            if method == 'ols':
                # 简单线性回归斜率
                A = np.column_stack([np.ones(len(factor)), factor])
                beta, _ = np.linalg.lstsq(A, ret, rcond=None)[0]
                return beta
            else:
                # 加权平均
                return np.average(ret, weights=factor)

        returns = merged.groupby('trade_date').apply(calc_daily_return)
        return returns.dropna().to_frame('factor_return')

    @staticmethod
    def calculate_group_returns(factor_df: pd.DataFrame,
                               forward_returns: pd.DataFrame,
                               n_groups: int = 5) -> Dict[str, Any]:
        """
        计算分组回测收益

        Args:
            factor_df: 因子数据
            forward_returns: 前瞻收益率
            n_groups: 分组数量

        Returns:
            Dict[str, Any]: 分组收益统计
        """
        merged = pd.merge(
            factor_df, forward_returns,
            on=['ts_code', 'trade_date'],
            how='inner'
        )

        if len(merged) == 0:
            return {}

        # 每日分组
        def assign_group(group):
            sorted_group = group.sort_values('factor')
            n = len(sorted_group)
            group_labels = pd.qcut(
                sorted_group['factor'],
                q=n_groups,
                labels=False,
                duplicates='drop'
            )
            return group_labels

        merged['group'] = merged.groupby('trade_date').apply(
            assign_group, include_groups=False
        ).reset_index(level=0, drop=True)

        # 计算各组收益
        group_returns = merged.groupby(['trade_date', 'group'])['forward_return'].mean().unstack()

        # 统计
        stats = {}
        for i in range(n_groups):
            if i in group_returns.columns:
                stats[f'group_{i+1}'] = float(group_returns[i].mean())

        # 最大分组差
        if len(group_returns.columns) > 1:
            max_group = group_returns.max(axis=1)
            min_group = group_returns.min(axis=1)
            stats['group_1_vs_5'] = float((max_group - min_group).mean())

        return stats

    @staticmethod
    def calculate_turnover(factor_df: pd.DataFrame) -> float:
        """
        计算换手率

        Args:
            factor_df: 因子数据 [ts_code, trade_date, factor]

        Returns:
            float: 平均换手率
        """
        if len(factor_df) < 2:
            return 0.0

        # 按日期排序
        df = factor_df.sort_values(['trade_date', 'ts_code'])

        # 获取每日股票池
        daily_stocks = df.groupby('trade_date')['ts_code'].apply(set)

        if len(daily_stocks) < 2:
            return 0.0

        turnover_list = []

        for i in range(1, len(daily_stocks)):
            prev_stocks = daily_stocks.iloc[i-1]
            curr_stocks = daily_stocks.iloc[i]

            if len(prev_stocks) == 0 or len(curr_stocks) == 0:
                continue

            # 换手率 = (新增 + 剔除) / 2 / 总数
            new_stocks = curr_stocks - prev_stocks
            removed_stocks = prev_stocks - curr_stocks

            turnover = (len(new_stocks) + len(removed_stocks)) / 2 / len(prev_stocks)
            turnover_list.append(turnover)

        if not turnover_list:
            return 0.0

        return float(np.mean(turnover_list))

    @staticmethod
    def calculate_stability(ic_series: pd.Series) -> Dict[str, float]:
        """
        计算因子稳定性

        Args:
            ic_series: IC时间序列

        Returns:
            Dict[str, float]: 稳定性指标
        """
        if len(ic_series) < 5:
            return {'stability': 0.0, 'stability_score': 0.0}

        # IC均值稳定性（滚动均值标准差）
        rolling_mean = ic_series.rolling(window=60, min_periods=5).mean()
        stability = rolling_mean.std()

        # 转换为0-100分（越小越稳定）
        stability_score = max(0, 100 - stability * 100)

        return {
            'stability': float(stability),
            'stability_score': float(stability_score),
            'ic_series_length': len(ic_series),
        }

    @staticmethod
    def calculate_comprehensive_score(metrics: Dict[str, Any]) -> float:
        """
        计算综合评分 (0-100)

        Args:
            metrics: 包含所有指标的字典

        Returns:
            float: 综合评分
        """
        score = 0.0
        weights = {
            'icir': 0.35,
            'stability': 0.25,
            'group_diff': 0.25,
            'turnover': 0.15,
        }

        # ICIR评分 (0-35分)
        icir = metrics.get('icir', 0)
        score += min(icir * 10, 35) * weights['icir']

        # 稳定性评分 (0-25分)
        stability = metrics.get('stability_score', 0)
        score += (stability / 100) * 25 * weights['stability']

        # 分组差异评分 (0-25分)
        group_diff = metrics.get('group_1_vs_5', 0)
        score += min(group_diff * 100, 25) * weights['group_diff']

        # 换手率评分 (0-15分，越低越好)
        turnover = metrics.get('turnover', 1)
        score += max(0, (1 - turnover) * 15) * weights['turnover']

        return min(score, 100.0)