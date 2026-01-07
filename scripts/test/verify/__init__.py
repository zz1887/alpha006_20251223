"""
文件input(依赖外部什么): factors, core.utils, pandas
文件output(提供什么): 验证脚本统一导入接口
文件pos(系统局部地位): 验证层，提供数据和逻辑验证功能
文件功能:
    1. 数据完整性验证
    2. 因子逻辑验证
    3. 计算结果验证
    4. 异常情况验证

使用示例:
    from scripts.test.verify import verify_factor_data, verify_calculation_logic

    # 验证因子数据
    is_valid = verify_factor_data(
        factor_df=factor_data,
        expected_range=(-5, 5)
    )

    # 验证计算逻辑
    is_correct = verify_calculation_logic(
        factor_name='alpha_peg',
        test_data=test_data,
        expected_result=expected
    )

返回值:
    bool: 验证结果
    Dict: 验证详情
    List: 错误列表

验证内容:
    1. 数据验证 - 完整性、正确性、一致性
    2. 逻辑验证 - 公式、边界、异常
    3. 结果验证 - 范围、分布、相关性
    4. 性能验证 - 速度、内存、稳定性
"""

__all__ = []
