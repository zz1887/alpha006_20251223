"""
文件input(依赖外部什么): unittest, pytest, factors, testing
文件output(提供什么): 测试脚本统一导入接口
文件pos(系统局部地位): 测试层，提供单元测试、集成测试、性能测试功能
文件功能:
    1. 单元测试（因子计算正确性）
    2. 集成测试（系统集成验证）
    3. 性能测试（处理能力评估）
    4. 回归测试（功能稳定性验证）

使用示例:
    from scripts.test import run_unit_tests, run_integration_tests

    # 运行单元测试
    run_unit_tests('alpha_peg')

    # 运行集成测试
    run_integration_tests()

    # 运行性能测试
    run_performance_tests()

返回值:
    bool: 测试通过状态
    Dict: 测试统计信息
    List: 失败测试列表

测试类型:
    1. 单元测试 - 单个函数/类验证
    2. 集成测试 - 模块间交互验证
    3. 性能测试 - 大数据量处理能力
    4. 回归测试 - 历史功能验证
"""

__all__ = []
