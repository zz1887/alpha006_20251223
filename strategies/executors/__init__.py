"""
文件input(依赖外部什么): factors, backtest, core.config, strategies.configs
文件output(提供什么): 策略执行器统一导入接口
文件pos(系统局部地位): 策略执行层，负责策略的具体执行逻辑
文件功能:
    1. 六因子策略执行器（six_factor_execute）
    2. 多因子策略执行器（strategy3_execute）
    3. 统一的策略执行接口

使用示例:
    from strategies.executors import six_factor_execute, strategy3_execute

    # 执行六因子策略
    result = six_factor_execute(
        start_date='20240101',
        end_date='20241231',
        version='standard'
    )

    # 执行多因子策略
    result = strategy3_execute(
        start_date='20240101',
        end_date='20241231',
        version='conservative'
    )

返回值:
    Dict: 策略执行结果（收益、风险、指标）
    bool: 执行状态

执行流程:
    1. 加载策略配置
    2. 获取因子数据
    3. 生成交易信号
    4. 执行交易操作
    5. 计算绩效指标
    6. 生成执行报告
"""

# 提供统一的执行接口
from .six_factor_executor import execute as six_factor_execute
from .strategy3_executor import execute as strategy3_execute

__all__ = [
    'six_factor_execute',
    'strategy3_execute',
]