"""
文件input(依赖外部什么): .six_factor_monthly, core.config
文件output(提供什么): 策略配置统一导入接口
文件pos(系统局部地位): 配置层的策略包入口, 统一管理所有策略配置
文件功能:
    1. 策略基本信息配置（名称、描述、版本）
    2. 因子配置（因子列表、权重、参数）
    3. 过滤配置（行业、市值、流动性过滤）
    4. 再平衡配置（调仓周期、持有天数）
    5. 交易成本配置（佣金、印花税、冲击成本）
    6. 回测配置（起止时间、基准、风险指标）
    7. 预期指标配置（目标ICIR、目标收益、最大回撤）

使用示例:
    from config.strategies import get_strategy_config, get_strategy_params

    # 获取策略配置
    config = get_strategy_config('six_factor_monthly')

    # 获取策略参数
    params = get_strategy_params('six_factor_monthly')

    # 使用配置
    factor_config = config['FACTOR_CONFIG']
    rebalance_days = config['REBALANCE_CONFIG']['rebalance_days']

返回值:
    Dict: 策略配置字典
    str: 配置项值
    function: 配置获取函数

配置内容:
    1. STRATEGY_INFO - 策略元信息（名称、描述、版本）
    2. FACTOR_CONFIG - 因子配置（列表、权重、参数）
    3. FILTER_CONFIG - 过滤条件（行业、市值、流动性）
    4. REBALANCE_CONFIG - 再平衡规则（周期、持有天数）
    5. TRADING_COST_CONFIG - 交易成本（佣金、印花税、冲击成本）
    6. BACKTEST_CONFIG - 回测参数（起止时间、基准）
    7. EXPECTED_METRICS - 预期目标（ICIR、收益、回撤）
    8. OUTPUT_CONFIG - 输出配置（报告、可视化）
"""

from .six_factor_monthly import (
    STRATEGY_INFO,
    FACTOR_CONFIG,
    FILTER_CONFIG,
    REBALANCE_CONFIG,
    TRADING_COST_CONFIG,
    BACKTEST_CONFIG,
    EXPECTED_METRICS,
    OUTPUT_CONFIG,
    get_strategy_config,
    get_strategy_params,
    STRATEGY_DESCRIPTION,
)

__all__ = [
    'six_factor_monthly',
    'STRATEGY_INFO',
    'FACTOR_CONFIG',
    'FILTER_CONFIG',
    'REBALANCE_CONFIG',
    'TRADING_COST_CONFIG',
    'BACKTEST_CONFIG',
    'EXPECTED_METRICS',
    'OUTPUT_CONFIG',
    'get_strategy_config',
    'get_strategy_params',
    'STRATEGY_DESCRIPTION',
]
