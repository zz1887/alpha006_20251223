"""
文件input(依赖外部什么): pandas, numpy, typing, sklearn.linear_model
文件output(提供什么): FactorCombiner类，提供多种因子组合和权重优化方法
文件pos(系统局部地位): 因子研究层，用于构建多因子组合和优化权重分配
文件功能:
    1. 等权组合（简单平均）
    2. IC加权组合（按IC均值分配权重）
    3. ICIR加权组合（按ICIR分配权重）
    4. 回归组合（按因子收益率回归系数分配权重）
    5. 因子权重优化（支持多种优化方法）
    6. 因子多样性检查（相关性分析）

使用示例:
    from factors.research.factor_combine import FactorCombiner

    # 等权组合
    combined = FactorCombiner.equal_weight_combination([factor1_df, factor2_df])

    # IC加权组合
    combined = FactorCombiner.ic_weighted_combination(
        [factor1_df, factor2_df],
        forward_returns,
        [ic1_series, ic2_series]
    )

    # ICIR加权组合
    combined = FactorCombiner.icir_weighted_combination(
        [factor1_df, factor2_df],
        forward_returns,
        [ic1_series, ic2_series]
    )

    # 回归组合
    combined = FactorCombiner.regression_combination(
        [factor1_df, factor2_df],
        forward_returns
    )

    # 权重优化
    combined, weights = FactorCombiner.optimize_factor_weights(
        [factor1_df, factor2_df],
        forward_returns,
        method='icir'
    )

    # 检查因子多样性
    diversity = FactorCombiner.check_factor_diversification([factor1_df, factor2_df])

参数说明:
    factor_dfs: 因子DataFrame列表，每个格式为 [ts_code, trade_date, factor]
    forward_returns: 前瞻收益率数据 [ts_code, trade_date, forward_return]
    ic_series_list: IC序列列表
    method: 优化方法 ('icir', 'ic', 'sharpe')

返回值:
    pd.DataFrame: 组合后的因子数据 [ts_code, trade_date, combined_factor]
    Tuple[pd.DataFrame, Dict]: (组合因子, 优化权重字典)
    Dict: 多样性评估结果
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from sklearn.linear_model import LinearRegression


class FactorCombiner:
    """
    因子组合器

    功能：
    1. 等权组合
    2. 因子IC加权组合
    3. 因子ICIR加权组合
    4. 因子优化组合
    """

    @staticmethod
    def equal_weight_combination(factor_dfs: List[pd.DataFrame]) -> pd.DataFrame:
        """
        等权组合因子

        Args:
            factor_dfs: 因子DataFrame列表

        Returns:
            pd.DataFrame: 组合后的因子
        """
        if not factor_dfs:
            raise ValueError("至少需要一个因子")

        # 合并所有因子
        merged = factor_dfs[0].copy()
        for i, df in enumerate(factor_dfs[1:], 1):
            merged = pd.merge(merged, df, on=['ts_code', 'trade_date'], how='inner')

        # 提取因子列
        factor_cols = [col for col in merged.columns if col not in ['ts_code', 'trade_date']]

        # 计算等权平均
        merged['combined_factor'] = merged[factor_cols].mean(axis=1)

        return merged[['ts_code', 'trade_date', 'combined_factor']]

    @staticmethod
    def ic_weighted_combination(factor_dfs: List[pd.DataFrame],
                                forward_returns: pd.DataFrame,
                                ic_series_list: List[pd.Series]) -> pd.DataFrame:
        """
        IC加权组合

        Args:
            factor_dfs: 因子DataFrame列表
            forward_returns: 前瞻收益率
            ic_series_list: 各因子的IC序列

        Returns:
            pd.DataFrame: IC加权组合后的因子
        """
        if len(factor_dfs) != len(ic_series_list):
            raise ValueError("因子数据和IC序列数量不匹配")

        # 计算各因子的平均IC绝对值作为权重
        weights = [abs(ic.mean()) for ic in ic_series_list]
        total_weight = sum(weights)
        if total_weight == 0:
            weights = [1.0 / len(weights)] * len(weights)
        else:
            weights = [w / total_weight for w in weights]

        # 合并因子数据
        merged = factor_dfs[0].copy()
        for i, df in enumerate(factor_dfs[1:], 1):
            merged = pd.merge(merged, df, on=['ts_code', 'trade_date'], how='inner')

        # 获取所有因子列
        factor_cols = [col for col in merged.columns if col not in ['ts_code', 'trade_date']]

        # 加权组合
        combined = np.zeros(len(merged))
        for i, col in enumerate(factor_cols):
            combined += merged[col].values * weights[i]

        merged['combined_factor'] = combined

        return merged[['ts_code', 'trade_date', 'combined_factor']]

    @staticmethod
    def icir_weighted_combination(factor_dfs: List[pd.DataFrame],
                                  forward_returns: pd.DataFrame,
                                  ic_series_list: List[pd.Series]) -> pd.DataFrame:
        """
        ICIR加权组合

        Args:
            factor_dfs: 因子DataFrame列表
            forward_returns: 前瞻收益率
            ic_series_list: 各因子的IC序列

        Returns:
            pd.DataFrame: ICIR加权组合后的因子
        """
        # 计算各因子的ICIR作为权重
        weights = []
        for ic_series in ic_series_list:
            if len(ic_series) > 1 and ic_series.std() != 0:
                icir = ic_series.mean() / ic_series.std()
                weights.append(abs(icir))
            else:
                weights.append(0.0)

        total_weight = sum(weights)
        if total_weight == 0:
            weights = [1.0 / len(weights)] * len(weights)
        else:
            weights = [w / total_weight for w in weights]

        # 合并因子数据
        merged = factor_dfs[0].copy()
        for i, df in enumerate(factor_dfs[1:], 1):
            merged = pd.merge(merged, df, on=['ts_code', 'trade_date'], how='inner')

        # 获取所有因子列
        factor_cols = [col for col in merged.columns if col not in ['ts_code', 'trade_date']]

        # 加权组合
        combined = np.zeros(len(merged))
        for i, col in enumerate(factor_cols):
            combined += merged[col].values * weights[i]

        merged['combined_factor'] = combined

        return merged[['ts_code', 'trade_date', 'combined_factor']]

    @staticmethod
    def regression_combination(factor_dfs: List[pd.DataFrame],
                              forward_returns: pd.DataFrame) -> pd.DataFrame:
        """
        回归组合（因子收益率加权）

        Args:
            factor_dfs: 因子DataFrame列表
            forward_returns: 前瞻收益率

        Returns:
            pd.DataFrame: 回归组合后的因子
        """
        # 合并所有因子
        merged = factor_dfs[0].copy()
        for i, df in enumerate(factor_dfs[1:], 1):
            merged = pd.merge(merged, df, on=['ts_code', 'trade_date'], how='inner')

        # 合并前瞻收益率
        merged = pd.merge(merged, forward_returns, on=['ts_code', 'trade_date'], how='inner')
        merged = merged.dropna()

        if len(merged) < 10:
            raise ValueError("数据量不足，无法进行回归分析")

        # 获取因子列
        factor_cols = [col for col in factor_dfs[0].columns if col not in ['ts_code', 'trade_date']]

        # 准备回归数据
        X = merged[factor_cols].values
        y = merged['forward_return'].values

        # 线性回归
        model = LinearRegression()
        model.fit(X, y)

        # 使用回归系数作为权重
        weights = np.abs(model.coef_)
        if weights.sum() == 0:
            weights = np.ones(len(weights)) / len(weights)
        else:
            weights = weights / weights.sum()

        # 计算加权组合因子
        combined = np.dot(X, weights)

        result = merged[['ts_code', 'trade_date']].copy()
        result['combined_factor'] = combined

        return result

    @staticmethod
    def optimize_factor_weights(factor_dfs: List[pd.DataFrame],
                               forward_returns: pd.DataFrame,
                               method: str = 'icir') -> Tuple[pd.DataFrame, Dict[str, float]]:
        """
        因子权重优化

        Args:
            factor_dfs: 因子DataFrame列表
            forward_returns: 前瞻收益率
            method: 优化方法 ('icir', 'ic', 'sharpe')

        Returns:
            Tuple: (组合因子, 优化权重)
        """
        # 计算各因子的IC序列
        from .metrics import FactorMetrics

        ic_series_list = []
        for df in factor_dfs:
            ic = FactorMetrics.calculate_ic(df, forward_returns)
            ic_series_list.append(ic)

        # 根据方法选择权重
        if method == 'icir':
            weights = [abs(ic.mean() / ic.std()) if ic.std() != 0 else 0
                      for ic in ic_series_list]
        elif method == 'ic':
            weights = [abs(ic.mean()) for ic in ic_series_list]
        elif method == 'sharpe':
            # 使用因子收益率的夏普比率
            weights = []
            for df in factor_dfs:
                fr = FactorMetrics.calculate_factor_return(df, forward_returns)
                if len(fr) > 1 and fr.std().iloc[0] != 0:
                    sharpe = fr.mean().iloc[0] / fr.std().iloc[0]
                    weights.append(abs(sharpe))
                else:
                    weights.append(0.0)
        else:
            raise ValueError(f"未知优化方法: {method}")

        # 归一化权重
        total = sum(weights)
        if total == 0:
            weights = [1.0 / len(weights)] * len(weights)
        else:
            weights = [w / total for w in weights]

        # 生成权重字典
        weight_dict = {}
        for i, df in enumerate(factor_dfs):
            factor_name = df.columns[2] if len(df.columns) > 2 else f'factor_{i+1}'
            weight_dict[factor_name] = weights[i]

        # 计算组合因子
        merged = factor_dfs[0].copy()
        for i, df in enumerate(factor_dfs[1:], 1):
            merged = pd.merge(merged, df, on=['ts_code', 'trade_date'], how='inner')

        factor_cols = [col for col in merged.columns if col not in ['ts_code', 'trade_date']]

        combined = np.zeros(len(merged))
        for i, col in enumerate(factor_cols):
            combined += merged[col].values * weights[i]

        merged['combined_factor'] = combined

        return merged[['ts_code', 'trade_date', 'combined_factor']], weight_dict

    @staticmethod
    def check_factor_diversification(factor_dfs: List[pd.DataFrame]) -> Dict[str, Any]:
        """
        检查因子多样性

        Args:
            factor_dfs: 因子DataFrame列表

        Returns:
            Dict: 多样性评估结果
        """
        # 计算平均相关性
        from .correlation import FactorCorrelationAnalyzer

        # 合并因子
        merged = factor_dfs[0].copy()
        for i, df in enumerate(factor_dfs[1:], 1):
            merged = pd.merge(merged, df, on=['ts_code', 'trade_date'], how='inner')

        if len(merged) == 0:
            return {'error': '无重叠数据'}

        analyzer = FactorCorrelationAnalyzer(merged)
        corr_matrix = analyzer.calculate_correlation()

        # 统计信息
        n_factors = len(corr_matrix.columns)
        avg_corr = corr_matrix.values[np.triu_indices_from(corr_matrix.values, k=1)].mean()

        # 多样性评分（0-100，越高越好）
        diversity_score = max(0, 100 * (1 - abs(avg_corr)))

        # 查找冗余对
        redundant_pairs = analyzer.find_redundant_factors(threshold=0.8)

        return {
            'num_factors': n_factors,
            'average_correlation': avg_corr,
            'diversity_score': diversity_score,
            'redundant_pairs_count': len(redundant_pairs),
            'is_diverse': diversity_score > 70 and len(redundant_pairs) == 0,
        }
