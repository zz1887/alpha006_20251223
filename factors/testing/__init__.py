"""
文件input(依赖外部什么): unittest, pandas, numpy, factors.core, factors.calculation, factors.evaluation
文件output(提供什么): 因子测试框架完整工具集统一导入接口
文件pos(系统局部地位): 因子测试层入口，提供因子验证和质量保证功能
文件功能:
    1. 单元测试（因子计算正确性验证）
    2. 集成测试（与评估系统集成验证）
    3. 性能测试（大数据量处理能力）
    4. 逻辑验证（异常值处理、边界情况）

使用示例:
    from factors.testing import create_test

    # 创建测试实例
    test = create_test('alpha_peg')

    # 运行单元测试
    test.run_all_tests()

    # 查看报告
    print(test.test_report)

    # 运行集成测试
    from factors.testing.integration_test import FactorIntegrationTest
    integration = FactorIntegrationTest()
    integration.run_integration_tests()

返回值:
    unittest.TestResult: 测试执行结果
    bool: 验证通过状态
    Dict: 测试统计信息

测试覆盖:
    1. ✅ 数据验证（正常/异常数据）
    2. ✅ 因子计算（格式/完整性/类型）
    3. ✅ 异常值处理（无穷值/NaN）
    4. ✅ 标准化（Z-score/Rank）
    5. ✅ 统计信息（字段/值合理性）
    6. ✅ 一致性（多次计算）
    7. ✅ 边界情况（空数据/小数据）
    8. ✅ 性能（大数据量）
    9. ✅ 评估集成（数据合并）
"""

from .unit_test import (
    FactorUnitTest,
    AlphaPegFactorTest,
    Alpha010FactorTest,
    create_test,
)
from .integration_test import FactorIntegrationTest
from .performance_test import PerformanceTest
from .validation import FactorValidator, validate_all_factors

__all__ = [
    # 单元测试
    'FactorUnitTest',
    'AlphaPegFactorTest',
    'Alpha010FactorTest',
    'create_test',

    # 集成测试
    'FactorIntegrationTest',

    # 性能测试
    'PerformanceTest',

    # 逻辑验证
    'FactorValidator',
    'validate_all_factors',
]