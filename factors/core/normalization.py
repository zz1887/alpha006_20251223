"""
文件input(依赖外部什么): pandas, numpy, scipy.stats
文件output(提供什么): 标准化工具类，提供多种数据标准化方法
文件pos(系统局部地位): 因子库核心工具，用于因子值标准化处理，确保不同因子可比性

功能:
    1. Z-score标准化
    2. Min-Max标准化
    3. Rank标准化
    4. 行业中性化
    5. 异常值处理（缩尾/截尾）

使用示例:
    from factors.core.normalization import Normalization

    # Z-score标准化
    normalized = Normalization.zscore(df, 'factor_value')

    # 行业中性化
    neutralized = Normalization.industry_neutralize(df, 'factor_value', 'industry')

    # 缩尾处理
    winsorized = Normalization.winsorize(df, 'factor_value', sigma=3.0)

返回值:
    pd.DataFrame: 标准化后的数据
"""

import pandas as pd
import numpy as np
from scipy import stats
from typing import Optional, Tuple


class Normalization:
    """
    标准化工具类

    提供因子值标准化的各种方法，确保不同因子之间可比
    """

    @staticmethod
    def zscore(df: pd.DataFrame, column: str, groupby: Optional[str] = None) -> pd.DataFrame:
        """
        Z-score标准化：(x - mean) / std

        Args:
            df: 数据框
            column: 需要标准化的列名
            groupby: 分组字段（如行业），按组内标准化

        Returns:
            pd.DataFrame: 包含标准化后数据的DataFrame
        """
        result = df.copy()

        if groupby and groupby in df.columns:
            # 分组标准化
            def zscore_group(group):
                values = group[column]
                mean = values.mean()
                std = values.std()
                if std == 0:
                    group[f'{column}_zscore'] = 0
                else:
                    group[f'{column}_zscore'] = (values - mean) / std
                return group

            result = result.groupby(groupby, group_keys=False).apply(zscore_group)
        else:
            # 全局标准化
            mean = result[column].mean()
            std = result[column].std()
            if std == 0:
                result[f'{column}_zscore'] = 0
            else:
                result[f'{column}_zscore'] = (result[column] - mean) / std

        return result

    @staticmethod
    def minmax(df: pd.DataFrame, column: str, groupby: Optional[str] = None) -> pd.DataFrame:
        """
        Min-Max标准化：(x - min) / (max - min)

        Args:
            df: 数据框
            column: 需要标准化的列名
            groupby: 分组字段

        Returns:
            pd.DataFrame: 包含标准化后数据的DataFrame
        """
        result = df.copy()

        if groupby and groupby in df.columns:
            def minmax_group(group):
                values = group[column]
                min_val = values.min()
                max_val = values.max()
                if max_val == min_val:
                    group[f'{column}_minmax'] = 0.5
                else:
                    group[f'{column}_minmax'] = (values - min_val) / (max_val - min_val)
                return group

            result = result.groupby(groupby, group_keys=False).apply(minmax_group)
        else:
            min_val = result[column].min()
            max_val = result[column].max()
            if max_val == min_val:
                result[f'{column}_minmax'] = 0.5
            else:
                result[f'{column}_minmax'] = (result[column] - min_val) / (max_val - min_val)

        return result

    @staticmethod
    def rank(df: pd.DataFrame, column: str, groupby: Optional[str] = None) -> pd.DataFrame:
        """
        Rank标准化：将值转换为排名（0-1）

        Args:
            df: 数据框
            column: 需要标准化的列名
            groupby: 分组字段

        Returns:
            pd.DataFrame: 包含标准化后数据的DataFrame
        """
        result = df.copy()

        if groupby and groupby in df.columns:
            def rank_group(group):
                values = group[column]
                rank = values.rank(method='average', na_option='keep')
                group[f'{column}_rank'] = rank / len(values.dropna())
                return group

            result = result.groupby(groupby, group_keys=False).apply(rank_group)
        else:
            rank = result[column].rank(method='average', na_option='keep')
            result[f'{column}_rank'] = rank / len(result[column].dropna())

        return result

    @staticmethod
    def industry_neutralize(df: pd.DataFrame,
                           factor_col: str,
                           industry_col: str,
                           method: str = 'residual') -> pd.DataFrame:
        """
        行业中性化：去除行业效应

        Args:
            df: 数据框
            factor_col: 因子列名
            industry_col: 行业列名
            method: 方法 ('residual' - 残差法, 'demean' - 均值扣除)

        Returns:
            pd.DataFrame: 包含中性化后数据的DataFrame
        """
        result = df.copy()

        if method == 'demean':
            # 方法1: 行业均值扣除
            industry_mean = df.groupby(industry_col)[factor_col].transform('mean')
            result[f'{factor_col}_neutral'] = df[factor_col] - industry_mean

        elif method == 'residual':
            # 方法2: 残差法（更精确）
            def residual_neutralize(group):
                y = group[factor_col].values
                x = np.ones(len(y))

                # 计算残差: y - mean(y)
                mean_y = np.mean(y)
                residuals = y - mean_y

                group[f'{factor_col}_neutral'] = residuals
                return group

            result = result.groupby(industry_col, group_keys=False).apply(residual_neutralize)

        return result

    @staticmethod
    def winsorize(df: pd.DataFrame, column: str, sigma: float = 3.0) -> pd.DataFrame:
        """
        缩尾处理：将超出均值±sigma*std的值替换为边界值

        Args:
            df: 数据框
            column: 需要处理的列名
            sigma: 异常值阈值（标准差倍数）

        Returns:
            pd.DataFrame: 包含缩尾后数据的DataFrame
        """
        result = df.copy()
        values = result[column].copy()

        mean = values.mean()
        std = values.std()

        if std == 0:
            result[f'{column}_winsorized'] = values
            return result

        lower_bound = mean - sigma * std
        upper_bound = mean + sigma * std

        # 缩尾处理
        values = values.clip(lower=lower_bound, upper=upper_bound)
        result[f'{column}_winsorized'] = values

        return result

    @staticmethod
    def truncate(df: pd.DataFrame, column: str, lower_quantile: float = 0.01,
                 upper_quantile: float = 0.99) -> pd.DataFrame:
        """
        截尾处理：删除超出分位数边界的行

        Args:
            df: 数据框
            column: 需要处理的列名
            lower_quantile: 下分位数（如0.01表示删除最低1%）
            upper_quantile: 上分位数（如0.99表示删除最高1%）

        Returns:
            pd.DataFrame: 截尾后的DataFrame
        """
        lower_bound = df[column].quantile(lower_quantile)
        upper_bound = df[column].quantile(upper_quantile)

        mask = (df[column] >= lower_bound) & (df[column] <= upper_bound)
        result = df[mask].copy()

        return result

    @staticmethod
    def standardize_all(df: pd.DataFrame,
                       factor_col: str,
                       industry_col: Optional[str] = None,
                       winsorize_sigma: float = 3.0,
                       normalize_method: str = 'zscore') -> pd.DataFrame:
        """
        完整标准化流程：缩尾 + 中性化 + 标准化

        Args:
            df: 数据框
            factor_col: 因子列名
            industry_col: 行业列名（可选）
            winsorize_sigma: 缩尾阈值
            normalize_method: 标准化方法 ('zscore', 'minmax', 'rank')

        Returns:
            pd.DataFrame: 完全标准化后的数据
        """
        result = df.copy()

        # 1. 缩尾处理
        result = Normalization.winsorize(result, factor_col, sigma=winsorize_sigma)
        factor_col_processed = f'{factor_col}_winsorized'

        # 2. 行业中性化（如果指定了行业）
        if industry_col and industry_col in result.columns:
            result = Normalization.industry_neutralize(
                result, factor_col_processed, industry_col
            )
            factor_col_processed = f'{factor_col_processed}_neutral'

        # 3. 标准化
        if normalize_method == 'zscore':
            result = Normalization.zscore(result, factor_col_processed)
            final_col = f'{factor_col_processed}_zscore'
        elif normalize_method == 'minmax':
            result = Normalization.minmax(result, factor_col_processed)
            final_col = f'{factor_col_processed}_minmax'
        elif normalize_method == 'rank':
            result = Normalization.rank(result, factor_col_processed)
            final_col = f'{factor_col_processed}_rank'
        else:
            raise ValueError(f"不支持的标准化方法: {normalize_method}")

        # 重命名最终列为标准名称
        result.rename(columns={final_col: 'factor_value'}, inplace=True)

        return result

    @staticmethod
    def get_normalization_stats(df: pd.DataFrame, column: str) -> dict:
        """
        获取标准化统计信息

        Args:
            df: 数据框
            column: 列名

        Returns:
            dict: 统计信息
        """
        values = df[column].dropna()

        return {
            'mean': float(values.mean()),
            'std': float(values.std()),
            'min': float(values.min()),
            'max': float(values.max()),
            'median': float(values.median()),
            'skewness': float(stats.skew(values)),
            'kurtosis': float(stats.kurtosis(values)),
            'valid_count': len(values),
            'missing_ratio': 1 - len(values) / len(df),
        }
