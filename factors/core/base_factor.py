"""
文件input(依赖外部什么): pandas, numpy, logging
文件output(提供什么): 因子计算基类，标准化因子接口
文件pos(系统局部地位): 因子库核心基础，所有因子类的父类
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union
import pandas as pd
import numpy as np
import logging


class BaseFactor(ABC):
    """
    因子计算基类

    所有因子必须继承此类，并实现以下抽象方法：
    - get_default_params(): 获取默认参数
    - calculate(): 核心计算逻辑
    - validate_data(): 数据验证
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        初始化因子

        Args:
            params: 因子参数字典，None时使用默认参数
        """
        self.params = params or self.get_default_params()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.data_cache = {}

    @abstractmethod
    def get_default_params(self) -> Dict[str, Any]:
        """
        获取默认参数

        Returns:
            Dict[str, Any]: 默认参数字典
        """
        pass

    @abstractmethod
    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        计算因子值

        Args:
            data: 输入数据，包含必需的字段

        Returns:
            pd.DataFrame: 包含ts_code, trade_date, factor_value的DataFrame
        """
        pass

    @abstractmethod
    def validate_data(self, data: pd.DataFrame) -> bool:
        """
        验证数据完整性

        Args:
            data: 待验证的数据

        Returns:
            bool: 数据是否有效
        """
        pass

    def get_factor_stats(self, factor_df: pd.DataFrame) -> Dict[str, Any]:
        """
        获取因子统计信息

        Args:
            factor_df: 因子计算结果

        Returns:
            Dict[str, Any]: 统计信息字典
        """
        if len(factor_df) == 0:
            return {}

        # 找到因子值列（排除ts_code和trade_date）
        factor_cols = [col for col in factor_df.columns
                      if col not in ['ts_code', 'trade_date']]

        if len(factor_cols) == 0:
            return {}

        factor_col = factor_cols[0]
        valid_data = factor_df[factor_col].dropna()

        if len(valid_data) == 0:
            return {}

        return {
            'total_records': len(factor_df),
            'stock_count': factor_df['ts_code'].nunique(),
            'date_count': factor_df['trade_date'].nunique(),
            'mean': float(valid_data.mean()),
            'std': float(valid_data.std()),
            'min': float(valid_data.min()),
            'max': float(valid_data.max()),
            'median': float(valid_data.median()),
            'missing_ratio': 1 - len(valid_data) / len(factor_df),
            'valid_records': len(valid_data),
        }

    def save_stats(self, stats: Dict[str, Any], filepath: str):
        """
        保存统计信息到文件

        Args:
            stats: 统计信息字典
            filepath: 保存路径
        """
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"因子统计信息 - {self.__class__.__name__}\n")
            f.write("=" * 50 + "\n\n")
            for key, value in stats.items():
                f.write(f"{key}: {value}\n")

    def __call__(self, data: pd.DataFrame) -> pd.DataFrame:
        """支持直接调用"""
        return self.calculate(data)

    def __repr__(self):
        return f"{self.__class__.__name__}(params={self.params})"