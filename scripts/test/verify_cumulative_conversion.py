#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证累计财务数据转换为单期数据的正确性

测试场景:
- 模拟Q1, Q2(半年报), Q3, Q4(年报)的累计数据
- 验证转换后的单期数据是否正确
"""

import sys
import os
sys.path.append('/home/zcy/alpha因子库')

import pandas as pd
import numpy as np
from factors.calculation.alpha_profit_employee import AlphaProfitEmployeeFactor

def test_cumulative_conversion():
    """测试累计数据转换"""
    print("=" * 80)
    print("累计财务数据转换验证测试")
    print("=" * 80)

    # 创建测试数据
    test_data = pd.DataFrame({
        'ts_code': ['600001.SH'] * 4 + ['600002.SH'] * 4,
        'ann_date': ['20240331', '20240630', '20240930', '20241231'] * 2,
        'operate_profit': [
            100,  # 600001.SH Q1: 100
            250,  # 600001.SH Q2: 250 (累计) -> Q2单期: 250-100=150
            400,  # 600001.SH Q3: 400 (累计) -> Q3单期: 400-250=150
            600,  # 600001.SH Q4: 600 (累计) -> Q4单期: 600-400=200
            200,  # 600002.SH Q1: 200
            350,  # 600002.SH Q2: 350 (累计) -> Q2单期: 350-200=150
            550,  # 600002.SH Q3: 550 (累计) -> Q3单期: 550-350=200
            800,  # 600002.SH Q4: 800 (累计) -> Q4单期: 800-550=250
        ],
        'c_paid_to_for_empl': [
            50,   # 600001.SH Q1: 50
            120,  # 600001.SH Q2: 120 (累计) -> Q2单期: 120-50=70
            200,  # 600001.SH Q3: 200 (累计) -> Q3单期: 200-120=80
            300,  # 600001.SH Q4: 300 (累计) -> Q4单期: 300-200=100
            80,   # 600002.SH Q1: 80
            170,  # 600002.SH Q2: 170 (累计) -> Q2单期: 170-80=90
            270,  # 600002.SH Q3: 270 (累计) -> Q3单期: 270-170=100
            400,  # 600002.SH Q4: 400 (累计) -> Q4单期: 400-270=130
        ],
        'total_mv': [10000, 10000, 10000, 10000, 20000, 20000, 20000, 20000]  # 万元
    })

    print("\n原始测试数据:")
    print(test_data.to_string(index=False))

    # 预期的单期数据
    expected_period_profit = [
        100,  # Q1
        150,  # Q2
        150,  # Q3
        200,  # Q4
        200,  # Q1
        150,  # Q2
        200,  # Q3
        250,  # Q4
    ]

    expected_period_employee_cash = [
        50,   # Q1
        70,   # Q2
        80,   # Q3
        100,  # Q4
        80,   # Q1
        90,   # Q2
        100,  # Q3
        130,  # Q4
    ]

    # 预期的因子值（分子/分母，单位转换：万元->元）
    # 分子 = period_profit + period_employee_cash
    # 分母 = total_mv * 10000
    expected_factors = [
        (100 + 50) / (10000 * 10000),      # 600001.SH Q1: 150/100M = 0.0000015
        (150 + 70) / (10000 * 10000),      # 600001.SH Q2: 220/100M = 0.0000022
        (150 + 80) / (10000 * 10000),      # 600001.SH Q3: 230/100M = 0.0000023
        (200 + 100) / (10000 * 10000),     # 600001.SH Q4: 300/100M = 0.0000030
        (200 + 80) / (20000 * 10000),      # 600002.SH Q1: 280/200M = 0.0000014
        (150 + 90) / (20000 * 10000),      # 600002.SH Q2: 240/200M = 0.0000012
        (200 + 100) / (20000 * 10000),     # 600002.SH Q3: 300/200M = 0.0000015
        (250 + 130) / (20000 * 10000),     # 600002.SH Q4: 380/200M = 0.0000019
    ]

    # 使用因子类进行计算
    factor = AlphaProfitEmployeeFactor()

    # 测试累计到单期转换
    print("\n" + "=" * 80)
    print("测试1: 累计数据转换为单期数据")
    print("=" * 80)

    period_profit = factor._convert_cumulative_to_period(test_data, 'operate_profit')
    period_employee_cash = factor._convert_cumulative_to_period(test_data, 'c_paid_to_for_empl')

    print("\n转换后的单期营业利润:")
    for i, (idx, val) in enumerate(period_profit.items()):
        expected = expected_period_profit[i]
        status = "✓" if abs(val - expected) < 1e-6 else "✗"
        print(f"  {test_data.loc[idx, 'ts_code']} {test_data.loc[idx, 'ann_date']}: {val:.0f} (预期: {expected:.0f}) {status}")

    print("\n转换后的单期职工现金:")
    for i, (idx, val) in enumerate(period_employee_cash.items()):
        expected = expected_period_employee_cash[i]
        status = "✓" if abs(val - expected) < 1e-6 else "✗"
        print(f"  {test_data.loc[idx, 'ts_code']} {test_data.loc[idx, 'ann_date']}: {val:.0f} (预期: {expected:.0f}) {status}")

    # 测试核心计算
    print("\n" + "=" * 80)
    print("测试2: 核心计算逻辑")
    print("=" * 80)

    factor_raw = factor._calculate_core_logic(test_data)

    print("\n计算得到的因子原始值:")
    for i, (idx, val) in enumerate(factor_raw.items()):
        expected = expected_factors[i]
        status = "✓" if abs(val - expected) < 1e-10 else "✗"
        print(f"  {test_data.loc[idx, 'ts_code']} {test_data.loc[idx, 'ann_date']}: {val:.10f} (预期: {expected:.10f}) {status}")

    # 验证所有值是否匹配
    all_match = True
    for i, (idx, val) in enumerate(factor_raw.items()):
        expected = expected_factors[i]
        if abs(val - expected) >= 1e-10:
            all_match = False
            break

    print("\n" + "=" * 80)
    if all_match:
        print("✓ 所有测试通过！累计数据转换逻辑正确。")
    else:
        print("✗ 测试失败！请检查转换逻辑。")
    print("=" * 80)

    return all_match

def test_edge_cases():
    """测试边界情况"""
    print("\n" + "=" * 80)
    print("边界情况测试")
    print("=" * 80)

    # 测试1: 缺失数据
    print("\n测试1: 包含缺失值的数据")
    test_data = pd.DataFrame({
        'ts_code': ['600001.SH'] * 4,
        'ann_date': ['20240331', '20240630', '20240930', '20241231'],
        'operate_profit': [100, np.nan, 400, 600],  # Q2缺失
        'c_paid_to_for_empl': [50, 120, 200, 300],
        'total_mv': [10000, 10000, 10000, 10000]
    })

    factor = AlphaProfitEmployeeFactor()
    result = factor._calculate_core_logic(test_data)
    print(f"  输入: {test_data['operate_profit'].tolist()}")
    print(f"  输出: {result.tolist()}")
    print(f"  Q2缺失导致后续无法计算: {pd.isna(result.iloc[1]) and pd.isna(result.iloc[2])}")

    # 测试2: 负值
    print("\n测试2: 包含负值的数据")
    test_data = pd.DataFrame({
        'ts_code': ['600001.SH'] * 4,
        'ann_date': ['20240331', '20240630', '20240930', '20241231'],
        'operate_profit': [100, 50, 400, 600],  # Q2单期为负值
        'c_paid_to_for_empl': [50, 120, 200, 300],
        'total_mv': [10000, 10000, 10000, 10000]
    })

    result = factor._calculate_core_logic(test_data)
    print(f"  输入: {test_data['operate_profit'].tolist()}")
    print(f"  输出: {result.tolist()}")
    print(f"  Q2负值被过滤: {pd.isna(result.iloc[1])}")

    # 测试3: 非连续季度
    print("\n测试3: 非连续季度数据")
    test_data = pd.DataFrame({
        'ts_code': ['600001.SH'] * 3,
        'ann_date': ['20240331', '20240930', '20241231'],  # 缺少Q2
        'operate_profit': [100, 400, 600],
        'c_paid_to_for_empl': [50, 200, 300],
        'total_mv': [10000, 10000, 10000]
    })

    result = factor._calculate_core_logic(test_data)
    print(f"  输入: {test_data['operate_profit'].tolist()}")
    print(f"  输出: {result.tolist()}")
    print(f"  Q3无法计算（缺少Q2）: {pd.isna(result.iloc[1])}")
    print(f"  Q4无法计算（缺少Q3累计）: {pd.isna(result.iloc[2])}")

if __name__ == '__main__':
    # 运行测试
    success = test_cumulative_conversion()
    test_edge_cases()

    if success:
        print("\n" + "=" * 80)
        print("累计数据转换验证完成：✓ 通过")
        print("=" * 80)
        sys.exit(0)
    else:
        print("\n" + "=" * 80)
        print("累计数据转换验证完成：✗ 失败")
        print("=" * 80)
        sys.exit(1)
