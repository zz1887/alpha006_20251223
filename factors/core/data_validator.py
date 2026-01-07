"""
文件input(依赖外部什么): pandas, numpy
文件output(提供什么): DataValidator类，提供数据验证功能
文件pos(系统局部地位): 因子库数据边界，确保输入数据质量，防止无效数据进入计算流程
文件功能:
    1. 必需字段检查
    2. 数据完整性检查
    3. 异常值检测
    4. 数据类型验证
    5. 数值范围验证
    6. 数据摘要生成

使用示例:
    from factors.core.data_validator import DataValidator

    # 完整验证
    required = ['ts_code', 'trade_date', 'pe_ttm', 'dt_netprofit_yoy']
    passed, errors = DataValidator.full_validation(data, required)

    # 获取数据摘要
    summary = DataValidator.get_data_summary(data)

参数说明:
    data: pandas DataFrame
    required_columns: 必需字段列表
    expected_types: 期望的数据类型字典
    min_valid_ratio: 最小有效数据比例 (默认0.8)
    sigma: 异常值阈值 (默认3.0)

返回值:
    Tuple[bool, str]: (是否通过, 错误信息)
    Tuple[bool, List[str]]: (是否通过, 错误列表)
    Dict[str, Any]: 数据摘要信息
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any


class DataValidator:
    """
    数据验证器 - 验证因子计算所需的数据质量

    功能：
    1. 必需字段检查
    2. 数据完整性检查
    3. 异常值检测
    4. 数据类型验证
    """

    @staticmethod
    def validate_required_columns(data: pd.DataFrame,
                                 required_columns: List[str]) -> Tuple[bool, str]:
        """
        验证必需字段

        Args:
            data: 数据框
            required_columns: 必需字段列表

        Returns:
            Tuple[bool, str]: (是否通过, 错误信息)
        """
        missing_cols = [col for col in required_columns if col not in data.columns]

        if missing_cols:
            return False, f"缺失必需字段: {missing_cols}"

        return True, "必需字段检查通过"

    @staticmethod
    def validate_data_completeness(data: pd.DataFrame,
                                   required_columns: List[str],
                                   min_valid_ratio: float = 0.8) -> Tuple[bool, str]:
        """
        验证数据完整性

        Args:
            data: 数据框
            required_columns: 需要检查的字段
            min_valid_ratio: 最小有效数据比例

        Returns:
            Tuple[bool, str]: (是否通过, 错误信息)
        """
        if len(data) == 0:
            return False, "数据为空"

        for col in required_columns:
            valid_ratio = data[col].notna().mean()

            if valid_ratio < min_valid_ratio:
                return False, f"字段 {col} 有效率过低: {valid_ratio:.2%} < {min_valid_ratio:.2%}"

        return True, "数据完整性检查通过"

    @staticmethod
    def validate_data_types(data: pd.DataFrame,
                           expected_types: Dict[str, type]) -> Tuple[bool, str]:
        """
        验证数据类型

        Args:
            data: 数据框
            expected_types: 期望的字段类型

        Returns:
            Tuple[bool, str]: (是否通过, 错误信息)
        """
        for col, expected_type in expected_types.items():
            if col not in data.columns:
                continue

            actual_type = data[col].dtype

            # 类型映射
            type_map = {
                'int64': int,
                'float64': float,
                'object': str,
                'datetime64[ns]': pd.Timestamp,
            }

            actual_type_name = type_map.get(str(actual_type), str(actual_type))

            if actual_type_name != expected_type:
                return False, f"字段 {col} 类型错误: 期望 {expected_type}, 实际 {actual_type}"

        return True, "数据类型检查通过"

    @staticmethod
    def detect_outliers(data: pd.DataFrame,
                       column: str,
                       sigma: float = 3.0) -> Tuple[bool, str]:
        """
        检测异常值

        Args:
            data: 数据框
            column: 检查的列
            sigma: 异常值阈值（标准差倍数）

        Returns:
            Tuple[bool, str]: (是否通过, 错误信息)
        """
        if column not in data.columns:
            return False, f"字段 {column} 不存在"

        values = data[column].dropna()

        if len(values) == 0:
            return False, f"字段 {column} 无有效数据"

        mean = values.mean()
        std = values.std()

        if std == 0:
            return True, "标准差为0，无法检测异常值"

        outliers = values[abs(values - mean) > sigma * std]

        if len(outliers) > 0:
            outlier_ratio = len(outliers) / len(values)
            return False, f"发现异常值: {len(outliers)}个 ({outlier_ratio:.2%})"

        return True, "无异常值"

    @staticmethod
    def validate_range(data: pd.DataFrame,
                      column: str,
                      min_val: Optional[float] = None,
                      max_val: Optional[float] = None) -> Tuple[bool, str]:
        """
        验证数值范围

        Args:
            data: 数据框
            column: 检查的列
            min_val: 最小值
            max_val: 最大值

        Returns:
            Tuple[bool, str]: (是否通过, 错误信息)
        """
        if column not in data.columns:
            return False, f"字段 {column} 不存在"

        values = data[column].dropna()

        if len(values) == 0:
            return False, f"字段 {column} 无有效数据"

        if min_val is not None and values.min() < min_val:
            return False, f"字段 {column} 包含小于 {min_val} 的值"

        if max_val is not None and values.max() > max_val:
            return False, f"字段 {column} 包含大于 {max_val} 的值"

        return True, "范围检查通过"

    @classmethod
    def full_validation(cls,
                       data: pd.DataFrame,
                       required_columns: List[str],
                       expected_types: Optional[Dict[str, type]] = None,
                       min_valid_ratio: float = 0.8) -> Tuple[bool, List[str]]:
        """
        完整验证流程

        Args:
            data: 数据框
            required_columns: 必需字段
            expected_types: 期望类型
            min_valid_ratio: 最小有效比例

        Returns:
            Tuple[bool, List[str]]: (是否通过, 错误列表)
        """
        errors = []

        # 1. 必需字段检查
        passed, msg = cls.validate_required_columns(data, required_columns)
        if not passed:
            errors.append(msg)

        # 2. 数据完整性检查
        passed, msg = cls.validate_data_completeness(data, required_columns, min_valid_ratio)
        if not passed:
            errors.append(msg)

        # 3. 数据类型检查
        if expected_types:
            passed, msg = cls.validate_data_types(data, expected_types)
            if not passed:
                errors.append(msg)

        return len(errors) == 0, errors

    @staticmethod
    def get_data_summary(data: pd.DataFrame) -> Dict[str, Any]:
        """
        获取数据摘要信息

        Args:
            data: 数据框

        Returns:
            Dict[str, Any]: 摘要信息
        """
        return {
            'total_rows': len(data),
            'total_columns': len(data.columns),
            'columns': list(data.columns),
            'memory_usage': data.memory_usage(deep=True).sum(),
            'missing_values': data.isna().sum().to_dict(),
            'dtypes': {col: str(dtype) for col, dtype in data.dtypes.items()},
        }