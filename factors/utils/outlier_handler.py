"""
文件input(依赖外部什么): pandas, numpy, scipy.stats, typing
文件output(提供什么): OutlierHandler类，提供完整的异常值检测和处理功能
文件pos(系统局部地位): 工具层，为因子数据提供专业的异常值处理服务
文件功能:
    1. 多种异常值检测方法（Z-score、IQR、MAD、百分位数）
    2. 异常值统计分析
    3. 异常值移除
    4. 异常值截断（缩尾）
    5. 按日期独立处理异常值
    6. 生成异常值分析报告

使用示例:
    from factors.utils.outlier_handler import OutlierHandler

    # 检测异常值
    outliers_zscore = OutlierHandler.detect_outliers_zscore(series, threshold=3.0)
    outliers_iqr = OutlierHandler.detect_outliers_iqr(series, factor=1.5)

    # 获取异常值统计
    stats = OutlierHandler.get_outlier_statistics(series, method='zscore', threshold=3.0)

    # 移除异常值
    clean_df = OutlierHandler.remove_outliers(df, ['factor'], method='zscore', threshold=3.0)

    # 截断异常值（缩尾）
    clipped_df = OutlierHandler.clip_outliers(df, ['factor'], method='percentile', lower_percentile=1.0, upper_percentile=99.0)

    # 按日期处理异常值
    daily_handled = OutlierHandler.handle_outliers_by_date(df, 'factor', method='clip', method='percentile')

    # 生成异常值报告
    report = OutlierHandler.generate_outlier_report(df, 'factor')

参数说明:
    series: 数据序列 (pd.Series)
    df: 输入数据 (pd.DataFrame)
    threshold: Z-score阈值（标准差倍数）
    factor: IQR乘数
    lower_percentile: 下限百分位
    upper_percentile: 上限百分位
    columns: 需要处理的列名列表
    method: 检测/处理方法
    factor_col: 因子列名
    methods: 多种检测方法列表

返回值:
    pd.Series: 布尔序列（异常值标记）
    Dict: 异常值统计信息
    pd.DataFrame: 处理后的数据
    Dict: 异常值分析报告
"""

import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, Tuple, Optional


class OutlierHandler:
    """
    异常值处理器

    功能：
    1. 异常值检测
    2. 异常值处理
    3. 异常值统计
    """

    @staticmethod
    def detect_outliers_zscore(series: pd.Series, threshold: float = 3.0) -> pd.Series:
        """
        使用Z-score检测异常值

        Args:
            series: 数据序列
            threshold: 阈值（标准差倍数）

        Returns:
            pd.Series: 布尔序列，True表示异常值
        """
        z_scores = np.abs((series - series.mean()) / series.std() if series.std() != 0 else 0)
        return z_scores > threshold

    @staticmethod
    def detect_outliers_iqr(series: pd.Series, factor: float = 1.5) -> pd.Series:
        """
        使用IQR（四分位距）检测异常值

        Args:
            series: 数据序列
            factor: IQR乘数

        Returns:
            pd.Series: 布尔序列，True表示异常值
        """
        Q1 = series.quantile(0.25)
        Q3 = series.quantile(0.75)
        IQR = Q3 - Q1

        lower_bound = Q1 - factor * IQR
        upper_bound = Q3 + factor * IQR

        return (series < lower_bound) | (series > upper_bound)

    @staticmethod
    def detect_outliers_modified_zscore(series: pd.Series, threshold: float = 3.5) -> pd.Series:
        """
        使用中位数绝对偏差（MAD）的改进Z-score检测异常值

        Args:
            series: 数据序列
            threshold: 阈值

        Returns:
            pd.Series: 布尔序列，True表示异常值
        """
        median = series.median()
        mad = np.median(np.abs(series - median))

        if mad == 0:
            return pd.Series(False, index=series.index)

        modified_z_scores = 0.6745 * (series - median) / mad
        return np.abs(modified_z_scores) > threshold

    @staticmethod
    def detect_outliers_percentile(series: pd.Series,
                                  lower_percentile: float = 1.0,
                                  upper_percentile: float = 99.0) -> pd.Series:
        """
        使用百分位数检测异常值

        Args:
            series: 数据序列
            lower_percentile: 下限百分位
            upper_percentile: 上限百分位

        Returns:
            pd.Series: 布尔序列，True表示异常值
        """
        lower = series.quantile(lower_percentile / 100)
        upper = series.quantile(upper_percentile / 100)

        return (series < lower) | (series > upper)

    @staticmethod
    def get_outlier_statistics(series: pd.Series,
                              method: str = 'zscore',
                              **kwargs) -> Dict[str, float]:
        """
        获取异常值统计信息

        Args:
            series: 数据序列
            method: 检测方法
            **kwargs: 方法参数

        Returns:
            Dict: 异常值统计
        """
        if method == 'zscore':
            outliers = OutlierHandler.detect_outliers_zscore(series, **kwargs)
        elif method == 'iqr':
            outliers = OutlierHandler.detect_outliers_iqr(series, **kwargs)
        elif method == 'modified_zscore':
            outliers = OutlierHandler.detect_outliers_modified_zscore(series, **kwargs)
        elif method == 'percentile':
            outliers = OutlierHandler.detect_outliers_percentile(series, **kwargs)
        else:
            raise ValueError(f"未知方法: {method}")

        total = len(series)
        outlier_count = outliers.sum()
        outlier_ratio = outlier_count / total if total > 0 else 0

        return {
            'total': total,
            'outlier_count': outlier_count,
            'outlier_ratio': outlier_ratio,
            'valid_count': total - outlier_count,
            'valid_ratio': 1 - outlier_ratio,
        }

    @staticmethod
    def remove_outliers(df: pd.DataFrame,
                       columns: List[str],
                       method: str = 'zscore',
                       **kwargs) -> pd.DataFrame:
        """
        移除异常值

        Args:
            df: 输入数据
            columns: 需要处理的列
            method: 检测方法
            **kwargs: 方法参数

        Returns:
            pd.DataFrame: 移除异常值后的数据
        """
        result = df.copy()

        for col in columns:
            if method == 'zscore':
                outliers = OutlierHandler.detect_outliers_zscore(result[col], **kwargs)
            elif method == 'iqr':
                outliers = OutlierHandler.detect_outliers_iqr(result[col], **kwargs)
            elif method == 'modified_zscore':
                outliers = OutlierHandler.detect_outliers_modified_zscore(result[col], **kwargs)
            elif method == 'percentile':
                outliers = OutlierHandler.detect_outliers_percentile(result[col], **kwargs)
            else:
                raise ValueError(f"未知方法: {method}")

            result = result[~outliers]

        return result

    @staticmethod
    def clip_outliers(df: pd.DataFrame,
                     columns: List[str],
                     method: str = 'percentile',
                     **kwargs) -> pd.DataFrame:
        """
        截断异常值（缩尾）

        Args:
            df: 输入数据
            columns: 需要处理的列
            method: 截断方法
            **kwargs: 方法参数

        Returns:
            pd.DataFrame: 截断异常值后的数据
        """
        result = df.copy()

        for col in columns:
            if method == 'percentile':
                lower = result[col].quantile(kwargs.get('lower_percentile', 1.0) / 100)
                upper = result[col].quantile(kwargs.get('upper_percentile', 99.0) / 100)
                result[col] = result[col].clip(lower=lower, upper=upper)

            elif method == 'zscore':
                mean = result[col].mean()
                std = result[col].std()
                if std > 0:
                    threshold = kwargs.get('threshold', 3.0)
                    lower = mean - threshold * std
                    upper = mean + threshold * std
                    result[col] = result[col].clip(lower=lower, upper=upper)

            elif method == 'iqr':
                Q1 = result[col].quantile(0.25)
                Q3 = result[col].quantile(0.75)
                IQR = Q3 - Q1
                factor = kwargs.get('factor', 1.5)
                lower = Q1 - factor * IQR
                upper = Q3 + factor * IQR
                result[col] = result[col].clip(lower=lower, upper=upper)

            else:
                raise ValueError(f"未知方法: {method}")

        return result

    @staticmethod
    def handle_outliers_by_date(df: pd.DataFrame,
                               factor_col: str,
                               method: str = 'zscore',
                               **kwargs) -> pd.DataFrame:
        """
        按日期处理异常值（每日独立处理）

        Args:
            df: 输入数据 [ts_code, trade_date, factor]
            factor_col: 因子列名
            method: 处理方法

        Returns:
            pd.DataFrame: 处理后的数据
        """
        def process_daily_data(group):
            if method == 'clip':
                return OutlierHandler.clip_outliers(group, [factor_col], **kwargs)[factor_col]
            elif method == 'remove':
                return OutlierHandler.remove_outliers(group, [factor_col], **kwargs)[factor_col]
            else:
                raise ValueError(f"未知方法: {method}")

        result = df.copy()
        result[factor_col] = result.groupby('trade_date').apply(
            lambda x: process_daily_data(x)
        ).reset_index(level=0, drop=True)

        return result

    @staticmethod
    def generate_outlier_report(df: pd.DataFrame,
                               factor_col: str,
                               methods: List[str] = None) -> Dict[str, Dict]:
        """
        生成异常值分析报告

        Args:
            df: 输入数据
            factor_col: 因子列名
            methods: 检测方法列表

        Returns:
            Dict: 异常值分析报告
        """
        if methods is None:
            methods = ['zscore', 'iqr', 'modified_zscore', 'percentile']

        series = df[factor_col].dropna()

        report = {}
        for method in methods:
            if method == 'zscore':
                stats = OutlierHandler.get_outlier_statistics(series, method='zscore', threshold=3.0)
            elif method == 'iqr':
                stats = OutlierHandler.get_outlier_statistics(series, method='iqr', factor=1.5)
            elif method == 'modified_zscore':
                stats = OutlierHandler.get_outlier_statistics(series, method='modified_zscore', threshold=3.5)
            elif method == 'percentile':
                stats = OutlierHandler.get_outlier_statistics(series, method='percentile',
                                                             lower_percentile=1.0, upper_percentile=99.0)

            report[method] = stats

        # 添加基础统计
        report['basic'] = {
            'mean': float(series.mean()),
            'std': float(series.std()),
            'min': float(series.min()),
            'max': float(series.max()),
            'median': float(series.median()),
            'skewness': float(series.skew()),
            'kurtosis': float(series.kurtosis()),
        }

        return report
