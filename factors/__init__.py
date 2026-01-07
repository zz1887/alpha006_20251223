"""
Alpha006因子库 - 统一入口

版本: v2.0
更新日期: 2026-01-06

功能说明:
- 提供统一的因子调用接口
- 支持因子注册和发现
- 标准化因子计算框架

使用示例:
    # 方式1: 通过注册器获取因子（推荐）
    from factors import FactorRegistry
    factor = FactorRegistry.get_factor('alpha_peg', version='standard')
    result = factor.calculate(data)

    # 方式2: 直接导入因子类
    from factors.calculation import AlphaPegFactor
    factor = AlphaPegFactor()
    result = factor.calculate(data)

    # 方式3: 注册所有因子后使用
    from scripts.factors.register_factors import register_all_factors
    register_all_factors()
    factor = FactorRegistry.get_factor('bias1_qfq')
    result = factor.calculate(data)
"""

# 核心基础层
from .core.base_factor import BaseFactor
from .core.factor_registry import FactorRegistry
from .core.data_validator import DataValidator

# 因子计算库（标准因子）
from .calculation import (
    AlphaPegFactor,
    Alpha010Factor,
    Alpha038Factor,
    Alpha120CqFactor,
    CrQfqFactor,
    AlphaPluseFactor,
    Bias1QfqFactor,
    AlphaProfitEmployeeFactor
)

__all__ = [
    # 核心基础层
    'BaseFactor',
    'FactorRegistry',
    'DataValidator',

    # 标准因子计算类
    'AlphaPegFactor',
    'Alpha010Factor',
    'Alpha038Factor',
    'Alpha120CqFactor',
    'CrQfqFactor',
    'AlphaPluseFactor',
    'Bias1QfqFactor',
    'AlphaProfitEmployeeFactor',
]