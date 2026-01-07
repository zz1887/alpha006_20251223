"""
文件input(依赖外部什么): pandas, numpy, BaseFactor, FactorRegistry
文件output(提供什么): Alpha010Factor类，提供4日价格趋势因子计算
文件pos(系统局部地位): 因子计算层，提供价格趋势因子标准化实现
文件功能: 计算4日价格变化率，衡量短期价格趋势和动量

数学公式: alpha_010 = (close - close_4d_ago) / close_4d_ago

使用示例:
    from factors.calculation.alpha_010 import Alpha010Factor
    factor = Alpha010Factor()
    result = factor.calculate(data)

    # 通过注册器获取
    from factors import FactorRegistry
    factor = FactorRegistry.get_factor('alpha_010', version='standard')
    result = factor.calculate(data)

参数说明:
    lookback_period: 回看周期（默认4天）
    outlier_sigma: 异常值阈值（默认3.0）
    normalization: 标准化方法（None/zscore/rank）
    industry_neutral: 是否行业中性化（默认False）
    min_period: 最小有效周期（默认3）

返回值:
    pd.DataFrame: [ts_code, trade_date, factor]
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from factors.core.base_factor import BaseFactor
from factors.core.factor_registry import FactorRegistry


class Alpha010Factor(BaseFactor):
    """
    Alpha 010因子 - 4日价格趋势因子

    因子说明:
    - 计算4日价格变化率
    - 正值表示上涨趋势，负值表示下跌趋势
    - 可用于捕捉短期价格动量

    参数说明:
    - lookback_period: 回看周期（默认4天）
    - outlier_sigma: 异常值阈值
    - normalization: 标准化方法
    - industry_neutral: 是否行业中性化
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)

    def get_default_params(self) -> Dict[str, Any]:
        """获取默认参数"""
        return {
            'lookback_period': 4,  # 回看4天
            'outlier_sigma': 3.0,
            'normalization': None,
            'industry_neutral': False,
            'min_period': 3,  # 最小有效周期
        }

    def validate_data(self, data: pd.DataFrame) -> bool:
        """
        数据验证

        必需字段:
        - ts_code: 股票代码
        - trade_date: 交易日期
        - close: 收盘价

        Args:
            data: 输入数据

        Returns:
            bool: 数据是否有效
        """
        required_columns = ['ts_code', 'trade_date', 'close']

        # 检查必需列
        for col in required_columns:
            if col not in data.columns:
                self.logger.error(f"缺少必需列: {col}")
                return False

        # 检查数据量
        if len(data) < 10:
            self.logger.error("数据量不足")
            return False

        return True

    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        计算010因子值

        计算流程:
        1. 数据验证
        2. 数据预处理（排序、分组）
        3. 核心计算：4日价格变化率
        4. 异常值处理
        5. 标准化（可选）
        6. 行业中性化（可选）

        Args:
            data: 输入数据
                必需列: ts_code, trade_date, close
                可选列: industry

        Returns:
            pd.DataFrame: 因子数据 [ts_code, trade_date, factor]
        """
        if not self.validate_data(data):
            raise ValueError("数据验证失败")

        # 1. 数据预处理
        df = data.copy()
        df = df.sort_values(['ts_code', 'trade_date'])

        # 2. 核心计算
        df['factor'] = self._calculate_core_logic(df)

        # 3. 异常值处理
        df = self._handle_outliers(df)

        # 4. 标准化（可选）
        df = self._normalize_factor(df)

        # 5. 行业中性化（可选）
        if self.params.get('industry_neutral', False):
            df = self._industry_neutralize(df)

        # 6. 返回结果
        result = df[['ts_code', 'trade_date', 'factor']].copy()
        result = result.dropna()

        self.logger.info(f"Alpha010因子计算完成，记录数: {len(result)}")
        return result

    def _calculate_core_logic(self, data: pd.DataFrame) -> pd.Series:
        """
        核心计算逻辑：4日价格变化率

        公式: (close - close_4d_ago) / close_4d_ago
        """
        period = self.params.get('lookback_period', 4)
        min_period = self.params.get('min_period', 3)

        # 按股票分组计算
        def calc_trend(group):
            if len(group) < min_period:
                return pd.Series([np.nan] * len(group), index=group.index)

            close = group['close'].values
            result = np.full(len(group), np.nan)

            for i in range(period, len(close)):
                if close[i-period] > 0:
                    result[i] = (close[i] - close[i-period]) / close[i-period]

            return pd.Series(result, index=group.index)

        return data.groupby('ts_code').apply(calc_trend).reset_index(level=0, drop=True)

    def _handle_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """异常值处理 - 缩尾处理"""
        sigma = self.params.get('outlier_sigma', 3.0)

        if 'factor' in df.columns:
            def clip_group(group):
                if len(group) < 2:
                    return group
                mean = group.mean()
                std = group.std()
                if std > 0:
                    lower = mean - sigma * std
                    upper = mean + sigma * std
                    return group.clip(lower=lower, upper=upper)
                return group

            df['factor'] = df.groupby('trade_date')['factor'].transform(clip_group)

        return df

    def _normalize_factor(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化"""
        method = self.params.get('normalization')

        if method is None or 'factor' not in df.columns:
            return df

        if method == 'zscore':
            df['factor'] = df.groupby('trade_date')['factor'].transform(
                lambda x: (x - x.mean()) / x.std() if x.std() != 0 else 0
            )
        elif method == 'rank':
            df['factor'] = df.groupby('trade_date')['factor'].rank(pct=True)

        return df

    def _industry_neutralize(self, df: pd.DataFrame) -> pd.DataFrame:
        """行业中性化"""
        if 'industry' not in df.columns:
            self.logger.warning("缺少行业数据，无法进行行业中性化")
            return df

        industry_mean = df.groupby(['trade_date', 'industry'])['factor'].transform('mean')
        df['factor'] = df['factor'] - industry_mean

        return df

    def get_factor_stats(self, factor_df: pd.DataFrame) -> Dict[str, Any]:
        """获取因子统计信息"""
        if len(factor_df) == 0:
            return {}

        valid_data = factor_df['factor'].dropna()

        return {
            'total_records': len(factor_df),
            'valid_records': len(valid_data),
            'missing_ratio': 1 - len(valid_data) / len(factor_df),
            'stock_count': factor_df['ts_code'].nunique(),
            'date_count': factor_df['trade_date'].nunique(),
            'mean': float(valid_data.mean()),
            'std': float(valid_data.std()),
            'min': float(valid_data.min()),
            'max': float(valid_data.max()),
            'median': float(valid_data.median()),
        }


# 注册因子
FactorRegistry.register('alpha_010', Alpha010Factor, 'price')
FactorRegistry.register('trend_4d', Alpha010Factor, 'price')  # 别名