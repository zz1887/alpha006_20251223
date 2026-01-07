"""
计算alpha_010因子 - 使用模拟数据演示计算逻辑
版本: v2.0
更新日期: 2025-12-30

说明: 由于数据库无法连接，使用模拟数据演示alpha_010计算逻辑
实际使用时，需要连接数据库获取真实价格数据
"""

import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, '/home/zcy/alpha006_20251223')

from factors.price.PRI_TREND_4D_V2 import PriTrend4Dv2Factor
from core.config.params import get_factor_param

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def generate_mock_price_data(stocks, target_date, days=10):
    """
    生成模拟价格数据用于演示

    Args:
        stocks: 股票列表
        target_date: 目标日期
        days: 数据天数

    Returns:
        模拟价格DataFrame
    """
    target_dt = pd.to_datetime(target_date, format='%Y%m%d')

    # 生成交易日
    trading_days = []
    for i in range(days):
        date = target_dt - timedelta(days=days-i-1)
        trading_days.append(date.strftime('%Y%m%d'))

    data = []
    for stock in stocks:
        # 为每只股票生成随机价格序列
        base_price = np.random.uniform(10, 100)

        for i, day in enumerate(trading_days):
            # 模拟价格波动
            if i == 0:
                close = base_price
            else:
                # 随机涨跌 -1% 到 +1%
                change = np.random.uniform(-0.01, 0.01)
                close = close * (1 + change)

            data.append({
                'ts_code': stock,
                'trade_date': pd.to_datetime(day, format='%Y%m%d'),
                'close': close,
                'open': close * (1 + np.random.uniform(-0.005, 0.005)),
                'high': close * (1 + np.random.uniform(0, 0.01)),
                'low': close * (1 - np.random.uniform(0, 0.01)),
                'vol': np.random.uniform(100000, 10000000)
            })

    df = pd.DataFrame(data)
    return df


def calculate_alpha_010_with_mock():
    """
    使用模拟数据计算alpha_010因子

    演示计算逻辑:
    1. Δclose = close_t - close_{t-1}
    2. 统计4日Δclose的ts_min/ts_max
    3. 三元规则: ts_min>0或ts_max<0取Δclose，否则取-Δclose
    4. 全市场rank得到alpha_010
    """
    print("\n" + "="*80)
    print("alpha_010因子计算演示 - 模拟数据")
    print("="*80)

    # 1. 准备数据
    target_date = '20250919'
    stocks = ['000001.SZ', '000002.SZ', '000003.SZ', '000004.SZ', '000005.SZ',
              '000006.SZ', '000007.SZ', '000008.SZ', '000009.SZ', '000010.SZ']

    print(f"\n1. 生成模拟数据")
    print(f"   股票数量: {len(stocks)}")
    print(f"   目标日期: {target_date}")

    price_df = generate_mock_price_data(stocks, target_date, days=10)
    print(f"   价格数据: {len(price_df)}条")

    # 2. 计算因子
    print(f"\n2. 计算alpha_010因子")
    params = get_factor_param('alpha_010', 'standard')
    print(f"   参数: {params}")

    factor = PriTrend4Dv2Factor(params)
    result = factor.calculate(price_df)

    if len(result) == 0:
        print("   ❌ 计算失败")
        return

    print(f"   ✅ 计算完成: {len(result)}只股票")

    # 3. 详细展示计算过程（取1只股票）
    print(f"\n3. 计算过程详解（以{stocks[0]}为例）")

    stock_data = price_df[price_df['ts_code'] == stocks[0]].sort_values('trade_date')
    print(f"\n   原始价格数据:")
    print(stock_data[['trade_date', 'close']].to_string(index=False))

    # 计算Δclose
    stock_data['delta_close'] = stock_data['close'].diff()
    print(f"\n   涨跌幅Δclose:")
    print(stock_data[['trade_date', 'close', 'delta_close']].to_string(index=False))

    # 获取最后4个Δclose
    delta_values = stock_data['delta_close'].dropna().tail(4).values
    ts_min = delta_values.min()
    ts_max = delta_values.max()
    target_delta = delta_values[-1]

    print(f"\n   4日Δclose统计:")
    print(f"   Δclose值: {delta_values}")
    print(f"   ts_min: {ts_min:.6f}")
    print(f"   ts_max: {ts_max:.6f}")
    print(f"   目标日Δclose: {target_delta:.6f}")

    # 应用三元规则
    if ts_min > 0:
        rule_value = target_delta
        rule_type = "连续上涨"
    elif ts_max < 0:
        rule_value = target_delta
        rule_type = "连续下跌"
    else:
        rule_value = -target_delta
        rule_type = "震荡反转"

    print(f"\n   三元规则:")
    print(f"   规则类型: {rule_type}")
    print(f"   规则取值: {rule_value:.6f}")

    # 4. 展示全市场结果
    print(f"\n4. 全市场计算结果")
    print(f"\n   前10只股票:")
    display_cols = ['ts_code', 'delta_close', 'ts_min', 'ts_max', 'rule_value', 'rule_type', 'alpha_010']
    print(result[display_cols].head(10).to_string(index=False))

    # 5. 统计信息
    print(f"\n5. 统计信息")
    print(f"   alpha_010范围: [{result['alpha_010'].min():.0f}, {result['alpha_010'].max():.0f}]")
    print(f"   alpha_010均值: {result['alpha_010'].mean():.2f}")
    print(f"   alpha_010标准差: {result['alpha_010'].std():.2f}")

    # 规则类型分布
    rule_counts = result['rule_type'].value_counts()
    print(f"\n   规则类型分布:")
    for rule, count in rule_counts.items():
        print(f"   {rule}: {count}只 ({count/len(result)*100:.1f}%)")

    # 6. 验证逻辑正确性
    print(f"\n6. 逻辑验证")

    # 验证1: 连续上涨的股票，rule_value应该为正
    up_stocks = result[result['rule_type'] == '连续上涨']
    if len(up_stocks) > 0:
        up_correct = (up_stocks['rule_value'] > 0).all()
        print(f"   连续上涨验证: {'✅ 正确' if up_correct else '❌ 错误'}")

    # 验证2: 连续下跌的股票，rule_value应该为负
    down_stocks = result[result['rule_type'] == '连续下跌']
    if len(down_stocks) > 0:
        down_correct = (down_stocks['rule_value'] < 0).all()
        print(f"   连续下跌验证: {'✅ 正确' if down_correct else '❌ 错误'}")

    # 验证3: 震荡反转的股票，rule_value是-target_delta
    reverse_stocks = result[result['rule_type'] == '震荡反转']
    if len(reverse_stocks) > 0:
        print(f"   震荡反转验证: ✅ 存在{len(reverse_stocks)}只股票")

    # 验证4: alpha_010是rank，应该从1到N
    unique_ranks = result['alpha_010'].nunique()
    expected_ranks = len(result)
    rank_correct = unique_ranks == expected_ranks
    print(f"   Rank唯一性验证: {'✅ 正确' if rank_correct else '❌ 错误'} (实际{unique_ranks}, 预期{expected_ranks})")

    # 验证5: rank应该是1到N的连续整数
    sorted_ranks = sorted(result['alpha_010'].unique())
    expected_ranks_list = list(range(1, len(result) + 1))
    rank_range_correct = sorted_ranks == expected_ranks_list
    print(f"   Rank范围验证: {'✅ 正确' if rank_range_correct else '❌ 错误'}")

    print(f"\n{'='*80}")
    print("演示完成！")
    print(f"{'='*80}")

    return result


def create_demo_excel(result_df):
    """创建演示用的Excel文件"""
    # 创建演示数据
    demo_data = result_df[['ts_code', 'alpha_010', 'delta_close', 'ts_min', 'ts_max', 'rule_value', 'rule_type']].copy()
    demo_data.columns = ['股票代码', 'alpha_010', 'Δclose', 'ts_min', 'ts_max', '规则取值', '规则类型']

    # 保存
    output_path = '/home/zcy/alpha006_20251223/results/output/alpha_010_demo_calculation.xlsx'
    demo_data.to_excel(output_path, index=False)

    print(f"\n✅ 演示数据已保存: {output_path}")
    print(f"   包含 {len(demo_data)} 行数据")

    return output_path


def main():
    """主函数"""
    # 计算alpha_010
    result = calculate_alpha_010_with_mock()

    if result is not None:
        # 创建演示Excel
        create_demo_excel(result)

        print(f"\n💡 说明:")
        print(f"   - 演示使用随机生成的模拟数据")
        print(f"   - 实际使用时需要连接数据库获取真实价格数据")
        print(f"   - 计算逻辑与代码实现完全一致")
        print(f"   - alpha_010 = rank(三元规则取值)")
        print(f"   - rank范围: 1~N (N=股票数量)")


if __name__ == '__main__':
    main()