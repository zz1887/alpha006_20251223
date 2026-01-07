"""
文件input(依赖外部什么): factors, backtest, core.config, pandas, numpy
文件output(提供什么): 策略基础类统一导入接口
文件pos(系统局部地位): 策略框架基础层，提供策略开发的基础架构
文件功能:
    1. BaseStrategy - 策略基类（定义策略接口和生命周期）
    2. StrategyRunner - 策略运行器（管理策略执行流程）

使用示例:
    from strategies.base import BaseStrategy, StrategyRunner

    # 创建自定义策略
    class MyStrategy(BaseStrategy):
        def initialize(self):
            # 初始化逻辑
            pass

        def handle_data(self, data):
            # 数据处理逻辑
            pass

        def generate_signals(self, data):
            # 信号生成逻辑
            pass

    # 运行策略
    runner = StrategyRunner('my_strategy')
    result = runner.run('20240101', '20241231')

返回值:
    BaseStrategy: 策略基类（抽象类）
    StrategyRunner: 策略运行器类

策略生命周期:
    1. initialize() - 初始化（加载数据、设置参数）
    2. handle_data() - 数据处理（接收市场数据）
    3. generate_signals() - 信号生成（产生交易信号）
    4. execute_trades() - 交易执行（执行买卖操作）
    5. calculate_metrics() - 指标计算（计算绩效指标）
"""

from .base_strategy import BaseStrategy
from .strategy_runner import StrategyRunner

__all__ = ['BaseStrategy', 'StrategyRunner']