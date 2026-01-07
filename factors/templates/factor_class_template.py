"""
文件input(依赖外部什么): pandas, numpy, typing, factors.core.base_factor, factors.core.factor_registry
文件output(提供什么): FactorNameFactor类，提供因子计算的标准模板和完整框架
文件pos(系统局部地位): 模板层，用于快速创建新的标准化因子类
文件功能:
    1. 提供因子类的基础结构（参数管理、数据验证、计算流程）
    2. 提供异常值处理、标准化、行业中性化等通用功能
    3. 提供因子统计信息计算
    4. 提供因子注册示例

使用示例:
    from factors.templates.factor_class_template import FactorNameFactor

    # 创建因子实例
    factor = FactorNameFactor({
        'outlier_sigma': 3.0,
        'normalization': 'zscore',
        'industry_neutral': False
    })

    # 计算因子
    result = factor.calculate(input_data)

    # 获取统计信息
    stats = factor.get_factor_stats(result)

参数说明:
    params: 参数字典
        - outlier_sigma: 异常值阈值（默认3.0）
        - normalization: 标准化方法（None/zscore/rank）
        - industry_neutral: 是否行业中性化（默认False）
        - lookback_period: 回看周期（默认20）

返回值:
    pd.DataFrame: 因子数据 [ts_code, trade_date, factor]
    Dict: 因子统计信息

开发步骤:
    1. 复制此文件并重命名为因子名.py
    2. 修改类名（如AlphaPegFactor）
    3. 实现_validate_data方法（数据验证）
    4. 实现_calculate_core_logic方法（核心计算）
    5. 如需要，重写行业数据加载逻辑
    6. 在文件末尾注册因子
    7. 在factors/__init__.py中导入
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from factors.core.base_factor import BaseFactor
from factors.core.factor_registry import FactorRegistry


class FactorNameFactor(BaseFactor):
    """
    因子名称说明

    因子类型: 估值/动量/质量/成长...
    因子逻辑: 简要描述因子计算逻辑
    适用场景: 股票筛选/行业轮动/风险控制...
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        初始化因子参数

        Args:
            params: 参数字典
                - outlier_sigma: 异常值阈值（默认3.0）
                - normalization: 标准化方法（None/zscore/rank）
                - industry_neutral: 是否行业中性化（默认False）
        """
        super().__init__(params)

    def get_default_params(self) -> Dict[str, Any]:
        """获取默认参数"""
        return {
            'outlier_sigma': 3.0,
            'normalization': None,
            'industry_neutral': False,
            'lookback_period': 20,
        }

    def validate_data(self, data: pd.DataFrame) -> bool:
        """
        数据验证

        Args:
            data: 输入数据，包含必需的字段

        Returns:
            bool: 数据是否有效
        """
        required_columns = ['ts_code', 'trade_date']  # 根据因子需求添加

        # 检查必需列
        for col in required_columns:
            if col not in data.columns:
                self.logger.error(f"缺少必需列: {col}")
                return False

        # 检查数据量
        if len(data) < 10:
            self.logger.error("数据量不足")
            return False

        # 检查空值
        if data[required_columns].isnull().any().any():
            self.logger.error("存在空值")
            return False

        return True

    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        计算因子值

        Args:
            data: 输入数据
                必需列: ts_code, trade_date
                可选列: 根据因子需求添加（如pe, pb, vol等）

        Returns:
            pd.DataFrame: 因子数据 [ts_code, trade_date, factor]
        """
        if not self.validate_data(data):
            raise ValueError("数据验证失败")

        # 1. 数据预处理
        df = data.copy()
        df = df.sort_values(['ts_code', 'trade_date'])

        # 2. 核心计算逻辑（根据具体因子实现）
        # 示例：计算因子值
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

        self.logger.info(f"因子计算完成，记录数: {len(result)}")
        return result

    def _calculate_core_logic(self, data: pd.DataFrame) -> pd.Series:
        """
        核心计算逻辑（需要子类实现）

        Args:
            data: 预处理后的数据

        Returns:
            pd.Series: 原始因子值
        """
        # 示例：这里需要根据具体因子实现
        # 比如：
        # return data['pe'] / data['growth_rate']
        # 或者
        # return data['close'].rolling(20).mean() / data['close']

        raise NotImplementedError("需要在子类中实现核心计算逻辑")

    def _handle_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """异常值处理"""
        sigma = self.params.get('outlier_sigma', 3.0)

        if 'factor' in df.columns:
            mean = df['factor'].mean()
            std = df['factor'].std()

            if std > 0:
                lower = mean - sigma * std
                upper = mean + sigma * std
                df['factor'] = df['factor'].clip(lower=lower, upper=upper)

        return df

    def _normalize_factor(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化"""
        method = self.params.get('normalization')

        if method is None or 'factor' not in df.columns:
            return df

        if method == 'zscore':
            # Z-score标准化
            df['factor'] = df.groupby('trade_date')['factor'].transform(
                lambda x: (x - x.mean()) / x.std() if x.std() != 0 else 0
            )

        elif method == 'rank':
            # 秩标准化
            df['factor'] = df.groupby('trade_date')['factor'].rank(pct=True)

        return df

    def _industry_neutralize(self, df: pd.DataFrame) -> pd.DataFrame:
        """行业中性化"""
        # 需要行业数据
        # 这里需要从外部传入行业数据或从数据库加载
        # 暂时返回原数据
        self.logger.warning("行业中性化需要行业数据，暂未实现")
        return df

    def get_factor_stats(self, factor_df: pd.DataFrame) -> Dict[str, Any]:
        """
        获取因子统计信息

        Args:
            factor_df: 因子数据

        Returns:
            Dict: 统计信息
        """
        if len(factor_df) == 0:
            return {}

        factor_col = 'factor'
        valid_data = factor_df[factor_col].dropna()

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


# 注册因子（重要！）
# FactorRegistry.register('factor_name', FactorNameFactor, 'category')
# 例如：
# FactorRegistry.register('alpha_peg', AlphaPegFactor, 'valuation')
