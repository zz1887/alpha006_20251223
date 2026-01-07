"""
文件input(依赖外部什么): pandas, numpy, typing
文件output(提供什么): DataProcessor类，提供数据清洗、标准化、中性化等处理功能
文件pos(系统局部地位): 工具层，为因子计算提供标准化的数据预处理服务
文件功能:
    1. 数据清洗（填充、删除空值）
    2. 数据标准化（Z-score、秩变换）
    3. 异常值处理（缩尾、移除、截断）
    4. 行业中性化处理
    5. 多因子数据合并
    6. 前瞻收益率计算

使用示例:
    from factors.utils.data_processor import DataProcessor

    # 数据清洗
    clean_df = DataProcessor.clean_data(df, fill_method='ffill', dropna=True)

    # Z-score标准化
    std_df = DataProcessor.standardize_zscore(df, group_by='trade_date')

    # 秩变换
    rank_df = DataProcessor.rank_transform(df, group_by='trade_date')

    # 缩尾处理
    winsorized_df = DataProcessor.winsorize(df, limits=(0.01, 0.99))

    # 行业中性化
    neutral_df = DataProcessor.neutralize_by_industry(df, 'factor', 'industry')

    # 合并多个因子
    merged_df = DataProcessor.merge_factor_data([factor1_df, factor2_df])

    # 计算前瞻收益率
    forward_returns = DataProcessor.calculate_forward_returns(price_df, hold_days=20)

参数说明:
    df: 输入DataFrame数据
    columns: 需要处理的列名列表
    group_by: 分组列名（用于分组标准化）
    fill_method: 填充方法 ('none', 'ffill', 'bfill', 'mean')
    dropna: 是否删除空值
    limits: 缩尾比例 (下限, 上限)
    factor_col: 因子列名
    industry_col: 行业列名
    factor_dfs: 因子DataFrame列表
    on: 合并键
    how: 合并方式
    price_df: 价格数据
    hold_days: 持有天数
    price_col: 价格列名
    method: 处理方法
    sigma: 标准差倍数

返回值:
    pd.DataFrame: 处理后的数据
"""

import pandas as pd
import numpy as np
from typing import Optional, List, Tuple


class DataProcessor:
    """
    数据处理器

    功能：
    1. 数据清洗
    2. 数据标准化
    3. 数据转换
    4. 数据合并
    """

    @staticmethod
    def clean_data(df: pd.DataFrame,
                   fill_method: str = 'none',
                   dropna: bool = True) -> pd.DataFrame:
        """
        数据清洗

        Args:
            df: 输入数据
            fill_method: 填充方法 ('none', 'ffill', 'bfill', 'mean')
            dropna: 是否删除空值

        Returns:
            pd.DataFrame: 清洗后的数据
        """
        result = df.copy()

        if fill_method == 'ffill':
            result = result.fillna(method='ffill')
        elif fill_method == 'bfill':
            result = result.fillna(method='bfill')
        elif fill_method == 'mean':
            result = result.fillna(result.mean())

        if dropna:
            result = result.dropna()

        return result

    @staticmethod
    def standardize_zscore(df: pd.DataFrame,
                          columns: List[str] = None,
                          group_by: Optional[str] = None) -> pd.DataFrame:
        """
        Z-score标准化

        Args:
            df: 输入数据
            columns: 需要标准化的列，None表示所有数值列
            group_by: 分组列名，None表示全局标准化

        Returns:
            pd.DataFrame: 标准化后的数据
        """
        result = df.copy()

        if columns is None:
            columns = df.select_dtypes(include=[np.number]).columns.tolist()

        if group_by:
            # 分组标准化
            for col in columns:
                result[col] = result.groupby(group_by)[col].transform(
                    lambda x: (x - x.mean()) / x.std() if x.std() != 0 else 0
                )
        else:
            # 全局标准化
            for col in columns:
                std = result[col].std()
                if std != 0:
                    result[col] = (result[col] - result[col].mean()) / std
                else:
                    result[col] = 0

        return result

    @staticmethod
    def rank_transform(df: pd.DataFrame,
                      columns: List[str] = None,
                      group_by: Optional[str] = None) -> pd.DataFrame:
        """
        秩变换（0-1标准化）

        Args:
            df: 输入数据
            columns: 需要变换的列
            group_by: 分组列名

        Returns:
            pd.DataFrame: 秩变换后的数据
        """
        result = df.copy()

        if columns is None:
            columns = df.select_dtypes(include=[np.number]).columns.tolist()

        if group_by:
            for col in columns:
                result[col] = result.groupby(group_by)[col].rank(pct=True)
        else:
            for col in columns:
                result[col] = result[col].rank(pct=True)

        return result

    @staticmethod
    def winsorize(df: pd.DataFrame,
                  columns: List[str] = None,
                  limits: Tuple[float, float] = (0.01, 0.99)) -> pd.DataFrame:
        """
        缩尾处理

        Args:
            df: 输入数据
            columns: 需要缩尾的列
            limits: 缩尾比例 (下限, 上限)

        Returns:
            pd.DataFrame: 缩尾后的数据
        """
        result = df.copy()

        if columns is None:
            columns = df.select_dtypes(include=[np.number]).columns.tolist()

        for col in columns:
            lower = result[col].quantile(limits[0])
            upper = result[col].quantile(limits[1])
            result[col] = result[col].clip(lower=lower, upper=upper)

        return result

    @staticmethod
    def neutralize_by_industry(df: pd.DataFrame,
                              factor_col: str,
                              industry_col: str = 'industry') -> pd.DataFrame:
        """
        行业中性化

        Args:
            df: 输入数据 [ts_code, trade_date, factor, industry]
            factor_col: 因子列名
            industry_col: 行业列名

        Returns:
            pd.DataFrame: 中性化后的因子
        """
        result = df.copy()

        # 计算行业均值
        industry_mean = result.groupby([industry_col, 'trade_date'])[factor_col].mean().reset_index()
        industry_mean.columns = [industry_col, 'trade_date', 'industry_mean']

        # 合并
        result = pd.merge(result, industry_mean, on=[industry_col, 'trade_date'], how='left')

        # 中性化：因子 - 行业均值
        result[f'{factor_col}_neutralized'] = result[factor_col] - result['industry_mean']

        return result

    @staticmethod
    def merge_factor_data(factor_dfs: List[pd.DataFrame],
                         on: List[str] = ['ts_code', 'trade_date'],
                         how: str = 'inner') -> pd.DataFrame:
        """
        合并多个因子数据

        Args:
            factor_dfs: 因子DataFrame列表
            on: 合并键
            how: 合并方式

        Returns:
            pd.DataFrame: 合并后的数据
        """
        if not factor_dfs:
            raise ValueError("至少需要一个因子数据")

        result = factor_dfs[0]

        for df in factor_dfs[1:]:
            result = pd.merge(result, df, on=on, how=how)

        return result

    @staticmethod
    def handle_outliers(df: pd.DataFrame,
                       columns: List[str] = None,
                       method: str = 'winsorize',
                       sigma: float = 3.0) -> pd.DataFrame:
        """
        异常值处理

        Args:
            df: 输入数据
            columns: 需要处理的列
            method: 处理方法 ('winsorize', 'remove', 'clip')
            sigma: 标准差倍数（用于remove和clip）

        Returns:
            pd.DataFrame: 处理后的数据
        """
        result = df.copy()

        if columns is None:
            columns = df.select_dtypes(include=[np.number]).columns.tolist()

        if method == 'winsorize':
            return DataProcessor.winsorize(result, columns)

        elif method == 'remove':
            for col in columns:
                mean = result[col].mean()
                std = result[col].std()
                if std > 0:
                    lower = mean - sigma * std
                    upper = mean + sigma * std
                    result = result[(result[col] >= lower) & (result[col] <= upper)]

        elif method == 'clip':
            for col in columns:
                mean = result[col].mean()
                std = result[col].std()
                if std > 0:
                    lower = mean - sigma * std
                    upper = mean + sigma * std
                    result[col] = result[col].clip(lower=lower, upper=upper)

        return result

    @staticmethod
    def calculate_forward_returns(price_df: pd.DataFrame,
                                 hold_days: int = 20,
                                 price_col: str = 'close') -> pd.DataFrame:
        """
        计算前瞻收益率

        Args:
            price_df: 价格数据 [ts_code, trade_date, close]
            hold_days: 持有天数
            price_col: 价格列名

        Returns:
            pd.DataFrame: 前瞻收益率 [ts_code, trade_date, forward_return]
        """
        df = price_df.sort_values(['ts_code', 'trade_date']).copy()

        # 计算未来价格
        df['future_price'] = df.groupby('ts_code')[price_col].shift(-hold_days)

        # 计算前瞻收益率
        df['forward_return'] = (df['future_price'] / df[price_col] - 1)

        # 保留有效数据
        result = df[['ts_code', 'trade_date', 'forward_return']].dropna()

        return result
