"""
文件input(依赖外部什么): factors.calculation.alpha_peg, factors.calculation.alpha_010, factors.calculation.alpha_038, factors.calculation.alpha_120cq, factors.calculation.cr_qfq, factors.calculation.alpha_pluse, factors.calculation.bias1_qfq
文件output(提供什么): 因子计算类统一导入接口和因子映射字典
文件pos(系统局部地位): 因子计算层入口，提供所有因子计算类的统一访问接口
文件功能:
    1. 统一导入所有因子计算类
    2. 提供因子名称到类的映射字典
    3. 支持两种调用方式（注册器/直接导入）

使用示例:
    # 方式1: 通过注册器获取（推荐）
    from factors import FactorRegistry
    factor = FactorRegistry.get_factor('alpha_peg')
    result = factor.calculate(data)

    # 方式2: 直接导入
    from factors.calculation import AlphaPegFactor
    factor = AlphaPegFactor()
    result = factor.calculate(data)

    # 方式3: 通过映射字典
    from factors.calculation import FACTOR_CLASSES
    factor_class = FACTOR_CLASSES['alpha_peg']
    factor = factor_class()
    result = factor.calculate(data)

返回值:
    Dict[str, Type]: 因子名称到类的映射字典
    List[str]: 可用因子列表
"""

from typing import Dict, Type

# 导入因子类
try:
    from .alpha_peg import AlphaPegFactor
    from .alpha_010 import Alpha010Factor
    from .alpha_038 import Alpha038Factor
    from .alpha_120cq import Alpha120CqFactor
    from .cr_qfq import CrQfqFactor
    from .alpha_pluse import AlphaPluseFactor
    from .bias1_qfq import Bias1QfqFactor
    from .alpha_profit_employee import AlphaProfitEmployeeFactor
    from .alpha_profit_employee_optimized import AlphaProfitEmployeeOptimizedFactor
except ImportError as e:
    # 如果依赖未安装，提供占位符并记录错误
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"导入因子类失败: {e}")
    AlphaPegFactor = None
    Alpha010Factor = None
    Alpha038Factor = None
    Alpha120CqFactor = None
    CrQfqFactor = None
    AlphaPluseFactor = None
    Bias1QfqFactor = None
    AlphaProfitEmployeeFactor = None
    AlphaProfitEmployeeOptimizedFactor = None

# 因子映射字典 - 注册所有标准因子
FACTOR_CLASSES: Dict[str, Type] = {
    'alpha_peg': AlphaPegFactor,
    'alpha_010': Alpha010Factor,
    'alpha_038': Alpha038Factor,
    'alpha_120cq': Alpha120CqFactor,
    'cr_qfq': CrQfqFactor,
    'alpha_pluse': AlphaPluseFactor,
    'bias1_qfq': Bias1QfqFactor,
    'alpha_profit_employee': AlphaProfitEmployeeFactor,
    'profit_employee': AlphaProfitEmployeeFactor,  # 别名
    'alpha_profit_employee_optimized': AlphaProfitEmployeeOptimizedFactor,
    'profit_employee_optimized': AlphaProfitEmployeeOptimizedFactor,  # 别名
}

# 可用因子列表
AVAILABLE_FACTORS = list(FACTOR_CLASSES.keys())

__all__ = [
    # 因子类
    'AlphaPegFactor',
    'Alpha010Factor',
    'Alpha038Factor',
    'Alpha120CqFactor',
    'CrQfqFactor',
    'AlphaPluseFactor',
    'Bias1QfqFactor',
    'AlphaProfitEmployeeFactor',
    'AlphaProfitEmployeeOptimizedFactor',
    # 工具
    'FACTOR_CLASSES',
    'AVAILABLE_FACTORS',
]