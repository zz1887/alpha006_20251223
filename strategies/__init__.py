"""
文件input(依赖外部什么): factors, backtest, core.config, pandas, numpy
文件output(提供什么): 策略框架统一导入接口
文件pos(系统局部地位): 策略框架层入口，提供策略开发、执行和管理的完整框架
文件功能:
    1. 策略基类（StrategyRunner）- 所有策略的父类
    2. 策略配置管理（configs）- 策略参数配置
    3. 策略执行器（executors）- 策略执行逻辑
    4. 策略实现（implementations）- 具体策略实现
    5. 策略运行器（runners）- 策略运行脚本

使用示例:
    from strategies import StrategyRunner, run_strategy, list_strategies

    # 列出所有策略
    strategies = list_strategies()

    # 运行策略
    result = run_strategy(
        name='six_factor_monthly',
        start_date='20240101',
        end_date='20241231',
        version='standard'
    )

    # 使用策略运行器
    runner = StrategyRunner('six_factor_monthly')
    performance = runner.run('20240101', '20241231')

返回值:
    Dict: 策略运行结果（收益、风险、指标）
    bool: 执行状态
    List: 策略列表

策略体系:
    1. base/ - 基础类（StrategyRunner, StrategyBase）
    2. configs/ - 配置管理（策略参数、因子权重）
    3. executors/ - 执行器（交易执行、仓位管理）
    4. implementations/ - 策略实现（六因子、多因子等）
    5. runners/ - 运行脚本（批量运行、监控）

当前策略:
    - six_factor_monthly: 六因子月末智能调仓策略
    - strategy3: 多因子综合得分策略
"""

from .base.strategy_runner import StrategyRunner

__version__ = '2.0'
__all__ = ['StrategyRunner']

# 策略列表
STRATEGIES = {
    'six_factor_monthly': '六因子月末智能调仓策略',
    'strategy3': '多因子综合得分策略',
}

def list_strategies():
    """列出所有策略"""
    return STRATEGIES

def run_strategy(name: str, start_date: str, end_date: str, version: str = 'standard', **kwargs):
    """
    运行策略

    Args:
        name: 策略名称
        start_date: 开始日期
        end_date: 结束日期
        version: 策略版本
        **kwargs: 其他参数

    Returns:
        是否成功
    """
    return StrategyRunner.run_strategy(name, start_date, end_date, version, **kwargs)
