"""
文件input(依赖外部什么): factors, backtest, strategies, core
文件output(提供什么): 执行脚本层统一入口
文件pos(系统局部地位): 执行脚本层入口，提供因子计算、回测、测试等完整工作流
文件功能:
    1. 因子计算脚本（批量计算、增量更新）
    2. 回测执行脚本（单因子回测、多因子组合）
    3. 测试验证脚本（单元测试、集成测试）
    4. 工具脚本（数据迁移、报告生成、性能分析）

使用示例:
    # 因子计算
    from scripts.factor_calc import run_factor_calculation
    run_factor_calculation('alpha_peg', '20240101', '20241231')

    # 回测执行
    from scripts.backtest import run_backtest
    result = run_backtest('six_factor_monthly', '20240101', '20241231')

    # 测试验证
    from scripts.test import run_unit_tests
    run_unit_tests('alpha_peg')

返回值:
    None: 脚本执行结果（通常输出到文件或控制台）
    Dict: 执行结果数据
    bool: 执行状态

脚本分类:
    1. factor_calc/ - 因子计算脚本（批量、增量、验证）
    2. backtest/ - 回测执行脚本（单期、多期、组合）
    3. test/ - 测试脚本（单元、集成、性能）
    4. tools/ - 工具脚本（数据处理、报告生成、分析）
"""

# 空文件，使目录成为Python包