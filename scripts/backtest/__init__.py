"""
文件input(依赖外部什么): factors, backtest, strategies, core.config
文件output(提供什么): 回测脚本统一导入接口
文件pos(系统局部地位): 回测执行层，提供单因子和多因子回测功能
文件功能:
    1. 六因子策略回测（优化版）
    2. 单因子回测（alpha_peg行业优化）
    3. 回测参数调优
    4. 回测结果分析

使用示例:
    from scripts.backtest import run_optimized_backtest, run_alpha_peg_industry_backtest

    # 运行优化回测
    result = run_optimized_backtest(
        strategy_name='six_factor_monthly',
        start_date='20240101',
        end_date='20241231'
    )

    # 运行单因子回测
    result = run_alpha_peg_industry_backtest(
        start_date='20240101',
        end_date='20241231'
    )

返回值:
    Dict: 回测结果（收益、风险、指标）
    pd.DataFrame: 回测详情
    bool: 执行状态

回测流程:
    1. 数据准备（因子数据、价格数据）
    2. 信号生成（因子排序、分组）
    3. 交易执行（模拟买卖、成本计算）
    4. 绩效计算（收益、风险、指标）
    5. 结果输出（报告、可视化）
"""

from .six_factor import SixFactorBacktestOptimized, run_optimized_backtest
from .alpha_peg_industry import run_backtest as run_alpha_peg_industry_backtest

__all__ = [
    'SixFactorBacktestOptimized',
    'run_optimized_backtest',
    'run_alpha_peg_industry_backtest',
]
