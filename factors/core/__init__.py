"""
文件input(依赖外部什么): abc, pandas, typing, logging, datetime
文件output(提供什么): 因子核心基础类和注册器统一导入接口
文件pos(系统局部地位): 因子库核心层入口，提供因子开发的基础架构和统一管理机制
文件功能:
    1. 因子基类（BaseFactor）- 所有因子的父类
    2. 因子注册器（FactorRegistry）- 插件式因子管理
    3. 数据验证器（DataValidator）- 输入数据质量检查

使用示例:
    # 创建自定义因子
    from factors.core import BaseFactor
    import pandas as pd

    class MyFactor(BaseFactor):
        def get_default_params(self):
            return {'threshold': 0.5}

        def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
            # 实现因子计算逻辑
            return data

        def validate_data(self, data: pd.DataFrame) -> bool:
            # 实现数据验证逻辑
            return 'ts_code' in data.columns

    # 注册因子
    from factors.core import FactorRegistry
    FactorRegistry.register('my_factor', MyFactor, 'custom')

    # 使用因子
    factor = FactorRegistry.get_factor('my_factor', version='standard')
    result = factor.calculate(data)

返回值:
    BaseFactor: 因子基类（抽象类）
    FactorRegistry: 因子注册器类
    DataValidator: 数据验证器类

核心设计:
    1. 统一接口：所有因子继承BaseFactor，实现标准接口
    2. 插件管理：通过注册器实现因子的动态加载和管理
    3. 版本控制：支持多版本参数配置（标准/保守/激进）
    4. 数据验证：确保输入数据符合因子计算要求
"""

from .base_factor import BaseFactor
from .factor_registry import FactorRegistry
from .data_validator import DataValidator

__all__ = ['BaseFactor', 'FactorRegistry', 'DataValidator']