"""
文件input(依赖外部什么): strategies.executors, strategies.configs, core.config
文件output(提供什么): 策略运行脚本统一导入接口
文件pos(系统局部地位): 策略运行层，提供统一的策略调用接口
文件功能:
    1. 策略批量运行脚本
    2. 策略单次运行脚本
    3. 策略监控和日志记录
    4. 策略结果输出

使用示例:
    from strategies.runners import run_six_factor_monthly

    # 运行六因子月度策略
    result = run_six_factor_monthly(
        start_date='20240101',
        end_date='20241231',
        version='standard'
    )

    # 批量运行多个版本
    from strategies.runners import run_strategy_batch

    results = run_strategy_batch(
        strategy_name='six_factor_monthly',
        versions=['standard', 'conservative', 'aggressive'],
        start_date='20240101',
        end_date='20241231'
    )

返回值:
    Dict: 策略运行结果
    List: 批量运行结果列表
    bool: 执行状态

运行模式:
    1. 单次运行 - 指定时间范围和版本
    2. 批量运行 - 多版本对比
    3. 定时运行 - 自动化调度
    4. 监控运行 - 实时监控和告警
"""

__all__ = []