"""
文件input(依赖外部什么): pandas, numpy, typing
文件output(提供什么): Validator类，提供完整的数据验证和质量检查功能
文件pos(系统局部地位): 工具层，为因子计算和回测提供数据质量保障
文件功能:
    1. DataFrame结构验证（列存在性、数据类型、重复数据）
    2. 因子数据质量验证（空值、无穷值、方差、异常值比例）
    3. 价格数据验证（价格有效性、波动性）
    4. 前瞻收益率验证（收益率范围、空值）
    5. 因子-收益率关系验证（重叠数据量、相关性）
    6. 数据完整性检查（覆盖率、稀疏度）
    7. 生成完整验证报告

使用示例:
    from factors.utils.validator import Validator

    # 验证因子数据结构
    valid, errors = Validator.validate_dataframe_structure(df, ['ts_code', 'trade_date', 'factor'])

    # 验证因子数据质量
    valid, errors = Validator.validate_factor_data(df, 'factor')

    # 验证价格数据
    valid, errors = Validator.validate_price_data(price_df)

    # 验证前瞻收益率
    valid, errors = Validator.validate_forward_returns(forward_returns)

    # 验证因子-收益率关系
    valid, errors = Validator.validate_factor_return_relationship(factor_df, forward_returns, min_overlap=30)

    # 生成完整验证报告
    report = Validator.generate_validation_report(df, 'factor', factor_col='factor')

    # 检查数据完整性
    completeness = Validator.check_data_completeness(df, expected_stocks=100, expected_dates=252)

参数说明:
    df: 待验证数据 (pd.DataFrame)
    required_columns: 必需列名列表
    optional_columns: 可选列名列表
    factor_col: 因子列名
    forward_returns: 前瞻收益率数据
    min_overlap: 最小重叠数据量
    data_type: 数据类型 ('factor', 'price', 'forward_return', 'relationship')
    expected_stocks: 期望股票数量
    expected_dates: 期望日期数量

返回值:
    Tuple[bool, List[str]]: (是否通过, 错误信息列表)
    Dict: 验证报告
    Dict: 完整性指标
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple


class Validator:
    """
    数据验证器

    功能：
    1. 数据格式验证
    2. 数据质量检查
    3. 业务规则验证
    4. 生成验证报告
    """

    @staticmethod
    def validate_dataframe_structure(df: pd.DataFrame,
                                    required_columns: List[str],
                                    optional_columns: List[str] = None) -> Tuple[bool, List[str]]:
        """
        验证DataFrame结构

        Args:
            df: 待验证数据
            required_columns: 必需列
            optional_columns: 可选列

        Returns:
            Tuple: (是否通过, 错误信息列表)
        """
        errors = []

        # 检查必需列
        for col in required_columns:
            if col not in df.columns:
                errors.append(f"缺少必需列: {col}")

        # 检查数据类型
        if 'ts_code' in df.columns and df['ts_code'].dtype != 'object':
            errors.append("ts_code应为字符串类型")

        if 'trade_date' in df.columns:
            if not pd.api.types.is_datetime64_any_dtype(df['trade_date']):
                errors.append("trade_date应为datetime类型")

        # 检查重复数据
        if 'ts_code' in df.columns and 'trade_date' in df.columns:
            duplicates = df.duplicated(subset=['ts_code', 'trade_date']).sum()
            if duplicates > 0:
                errors.append(f"发现{duplicates}条重复数据")

        return len(errors) == 0, errors

    @staticmethod
    def validate_factor_data(df: pd.DataFrame,
                            factor_col: str = 'factor') -> Tuple[bool, List[str]]:
        """
        验证因子数据质量

        Args:
            df: 因子数据 [ts_code, trade_date, factor]
            factor_col: 因子列名

        Returns:
            Tuple: (是否通过, 错误信息列表)
        """
        errors = []

        # 基础结构验证
        required_cols = ['ts_code', 'trade_date', factor_col]
        valid, structure_errors = Validator.validate_dataframe_structure(df, required_cols)
        errors.extend(structure_errors)

        if not valid:
            return False, errors

        # 检查因子列数据类型
        if not pd.api.types.is_numeric_dtype(df[factor_col]):
            errors.append(f"因子列{factor_col}应为数值类型")

        # 检查空值
        null_count = df[factor_col].isnull().sum()
        if null_count > 0:
            errors.append(f"因子列存在{null_count}个空值")

        # 检查无穷值
        inf_count = np.isinf(df[factor_col]).sum()
        if inf_count > 0:
            errors.append(f"因子列存在{inf_count}个无穷值")

        # 检查是否全为零
        if (df[factor_col] == 0).all():
            errors.append("因子列全为零")

        # 检查方差
        variance = df[factor_col].var()
        if variance == 0:
            errors.append("因子方差为零")

        # 检查异常值比例
        if len(df) > 0:
            q1 = df[factor_col].quantile(0.25)
            q3 = df[factor_col].quantile(0.75)
            iqr = q3 - q1
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            outlier_ratio = ((df[factor_col] < lower) | (df[factor_col] > upper)).sum() / len(df)

            if outlier_ratio > 0.2:
                errors.append(f"异常值比例过高: {outlier_ratio:.2%}")

        return len(errors) == 0, errors

    @staticmethod
    def validate_price_data(df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        验证价格数据

        Args:
            df: 价格数据 [ts_code, trade_date, close]

        Returns:
            Tuple: (是否通过, 错误信息列表)
        """
        errors = []

        valid, structure_errors = Validator.validate_dataframe_structure(df, ['ts_code', 'trade_date', 'close'])
        errors.extend(structure_errors)

        if not valid:
            return False, errors

        # 检查价格有效性
        if (df['close'] <= 0).any():
            errors.append("存在非正价格")

        # 检查价格波动
        price_stats = df.groupby('ts_code')['close'].agg(['min', 'max', 'std'])
        if (price_stats['std'] == 0).any():
            errors.append("存在价格无波动的股票")

        return len(errors) == 0, errors

    @staticmethod
    def validate_forward_returns(df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        验证前瞻收益率数据

        Args:
            df: 前瞻收益率数据 [ts_code, trade_date, forward_return]

        Returns:
            Tuple: (是否通过, 错误信息列表)
        """
        errors = []

        valid, structure_errors = Validator.validate_dataframe_structure(df, ['ts_code', 'trade_date', 'forward_return'])
        errors.extend(structure_errors)

        if not valid:
            return False, errors

        # 检查收益率范围
        if (df['forward_return'] < -0.99).any():
            errors.append("存在极端负收益率 (< -99%)")

        if (df['forward_return'] > 10).any():
            errors.append("存在极端正收益率 (> 1000%)")

        # 检查空值
        null_count = df['forward_return'].isnull().sum()
        if null_count > 0:
            errors.append(f"存在{null_count}个空值")

        return len(errors) == 0, errors

    @staticmethod
    def validate_factor_return_relationship(factor_df: pd.DataFrame,
                                           forward_returns: pd.DataFrame,
                                           min_overlap: int = 30) -> Tuple[bool, List[str]]:
        """
        验证因子与收益率的关系

        Args:
            factor_df: 因子数据
            forward_returns: 前瞻收益率
            min_overlap: 最小重叠数据量

        Returns:
            Tuple: (是否通过, 错误信息列表)
        """
        errors = []

        # 合并数据
        merged = pd.merge(factor_df, forward_returns, on=['ts_code', 'trade_date'], how='inner')

        if len(merged) < min_overlap:
            errors.append(f"重叠数据不足: {len(merged)} < {min_overlap}")

        # 检查相关性
        if len(merged) >= 10:
            corr = merged['factor'].corr(merged['forward_return'])
            if abs(corr) < 0.01:
                errors.append(f"因子与收益率相关性过低: {corr:.4f}")

        return len(errors) == 0, errors

    @staticmethod
    def generate_validation_report(df: pd.DataFrame,
                                  data_type: str,
                                  **kwargs) -> Dict:
        """
        生成完整验证报告

        Args:
            df: 待验证数据
            data_type: 数据类型 ('factor', 'price', 'forward_return')
            **kwargs: 额外参数

        Returns:
            Dict: 验证报告
        """
        report = {
            'data_type': data_type,
            'record_count': len(df),
            'stock_count': df['ts_code'].nunique() if 'ts_code' in df.columns else 0,
            'date_count': df['trade_date'].nunique() if 'trade_date' in df.columns else 0,
            'validation_passed': False,
            'errors': [],
            'warnings': [],
        }

        if data_type == 'factor':
            valid, errors = Validator.validate_factor_data(df, kwargs.get('factor_col', 'factor'))
            report['validation_passed'] = valid
            report['errors'] = errors

            # 额外统计
            if 'factor' in df.columns:
                report['factor_stats'] = {
                    'mean': float(df['factor'].mean()),
                    'std': float(df['factor'].std()),
                    'missing_ratio': float(df['factor'].isnull().mean()),
                }

        elif data_type == 'price':
            valid, errors = Validator.validate_price_data(df)
            report['validation_passed'] = valid
            report['errors'] = errors

        elif data_type == 'forward_return':
            valid, errors = Validator.validate_forward_returns(df)
            report['validation_passed'] = valid
            report['errors'] = errors

        elif data_type == 'relationship':
            factor_df = kwargs.get('factor_df')
            forward_returns = kwargs.get('forward_returns')
            if factor_df is not None and forward_returns is not None:
                valid, errors = Validator.validate_factor_return_relationship(
                    factor_df, forward_returns, kwargs.get('min_overlap', 30)
                )
                report['validation_passed'] = valid
                report['errors'] = errors

        return report

    @staticmethod
    def check_data_completeness(df: pd.DataFrame,
                               expected_stocks: Optional[int] = None,
                               expected_dates: Optional[int] = None) -> Dict[str, float]:
        """
        检查数据完整性

        Args:
            df: 数据
            expected_stocks: 期望股票数
            expected_dates: 期望日期数

        Returns:
            Dict: 完整性指标
        """
        completeness = {}

        if 'ts_code' in df.columns:
            actual_stocks = df['ts_code'].nunique()
            completeness['stock_coverage'] = actual_stocks / expected_stocks if expected_stocks else 1.0

        if 'trade_date' in df.columns:
            actual_dates = df['trade_date'].nunique()
            completeness['date_coverage'] = actual_dates / expected_dates if expected_dates else 1.0

        # 稀疏度
        if 'ts_code' in df.columns and 'trade_date' in df.columns:
            total_possible = df['ts_code'].nunique() * df['trade_date'].nunique()
            completeness['sparsity'] = 1 - len(df) / total_possible if total_possible > 0 else 0

        return completeness
