"""
alpha_pluse因子 - 快速验证脚本

功能:
1. 使用样本数据验证计算逻辑
2. 展示详细的计算步骤
3. 验证结果正确性
"""

import pandas as pd
import numpy as np
from datetime import datetime


def create_test_data():
    """创建测试数据"""
    print("\n" + "="*80)
    print("创建测试数据")
    print("="*80)

    # 生成30天数据
    dates = pd.date_range('2025-01-01', '2025-01-30', freq='D')

    # 股票A: 预期 alpha_pluse=1 (2-4天满足)
    # 14日均值约100，满足条件: 140-350
    vol_a = [100] * 30
    vol_a[10] = 200  # 2倍 ✓
    vol_a[15] = 250  # 2.5倍 ✓
    vol_a[20] = 300  # 3倍 ✓
    # 总计3天满足

    # 股票B: 预期 alpha_pluse=0 (1天满足，小于2)
    vol_b = [80] * 30
    vol_b[12] = 150  # 1.875倍 ✓
    # 总计1天满足

    # 股票C: 预期 alpha_pluse=0 (5天满足，大于4)
    vol_c = [120] * 30
    vol_c[5] = 200   # 1.67倍 ✓
    vol_c[8] = 220   # 1.83倍 ✓
    vol_c[12] = 250  # 2.08倍 ✓
    vol_c[18] = 280  # 2.33倍 ✓
    vol_c[25] = 300  # 2.5倍 ✓
    # 总计5天满足

    # 股票D: 预期 alpha_pluse=1 (2天满足，边界情况)
    vol_d = [100] * 30
    vol_d[10] = 140  # 1.4倍 ✓ (下限)
    vol_d[20] = 350  # 3.5倍 ✓ (上限)
    # 总计2天满足

    data = []
    for i, date in enumerate(dates):
        data.append({'ts_code': 'A', 'trade_date': date, 'vol': vol_a[i]})
        data.append({'ts_code': 'B', 'trade_date': date, 'vol': vol_b[i]})
        data.append({'ts_code': 'C', 'trade_date': date, 'vol': vol_c[i]})
        data.append({'ts_code': 'D', 'trade_date': date, 'vol': vol_d[i]})

    df = pd.DataFrame(data)
    print(f"生成 {len(df)} 条数据，4只股票，30天")
    return df


def manual_calculation_demo(df):
    """手动计算演示 - 以股票A为例"""
    print("\n" + "="*80)
    print("手动计算演示 - 股票A")
    print("="*80)

    stock_a = df[df['ts_code'] == 'A'].sort_values('trade_date').reset_index(drop=True)
    stock_a['vol_14_mean'] = stock_a['vol'].rolling(14, min_periods=14).mean()

    print("\n数据预览 (最后10天):")
    print(f"{'日期':<12} {'成交量':<8} {'14日均值':<10} {'倍数':<8} {'满足':<6}")
    print("-" * 60)

    for i in range(len(stock_a)):
        row = stock_a.iloc[i]
        date = row['trade_date'].strftime('%Y-%m-%d')
        vol = row['vol']
        mean = row['vol_14_mean']

        if pd.notna(mean) and mean > 0:
            multiple = vol / mean
            condition = 1.4 <= multiple <= 3.5
            print(f"{date:<12} {vol:<8} {mean:<10.2f} {multiple:<8.2f} {'✓' if condition else '✗':<6}")
        else:
            print(f"{date:<12} {vol:<8} {'N/A':<10} {'N/A':<8} {'N/A':<6}")

    # 计算20日滚动满足数量
    print("\n20日滚动统计:")
    for i in range(19, len(stock_a)):
        window_start = max(0, i - 19)
        window_data = stock_a.iloc[window_start:i+1]

        count = 0
        for _, row in window_data.iterrows():
            if pd.notna(row['vol_14_mean']) and row['vol_14_mean'] > 0:
                multiple = row['vol'] / row['vol_14_mean']
                if 1.4 <= multiple <= 3.5:
                    count += 1

        date = stock_a.iloc[i]['trade_date'].strftime('%Y-%m-%d')
        alpha = 1 if 2 <= count <= 4 else 0
        print(f"{date}: {count} 天满足 -> alpha_pluse={alpha}")


def calculate_alpha_pluse(df):
    """计算alpha_pluse因子"""
    print("\n" + "="*80)
    print("计算alpha_pluse因子")
    print("="*80)

    results = []

    for ts_code, group in df.groupby('ts_code'):
        group = group.sort_values('trade_date').copy()

        # 计算14日成交量均值
        group['vol_14_mean'] = group['vol'].rolling(14, min_periods=14).mean()

        # 标记满足条件的交易日
        group['condition'] = (
            (group['vol'] >= group['vol_14_mean'] * 1.4) &
            (group['vol'] <= group['vol_14_mean'] * 3.5) &
            group['vol_14_mean'].notna()
        )

        # 计算20日滚动满足数量
        def count_conditions(idx):
            if idx < 19:
                return np.nan
            window_data = group.iloc[idx - 19:idx + 1]
            return window_data['condition'].sum()

        group['count_20d'] = [count_conditions(i) for i in range(len(group))]

        # 计算alpha_pluse
        group['alpha_pluse'] = (
            (group['count_20d'] >= 2) &
            (group['count_20d'] <= 4)
        ).astype(int)

        results.append(group[['ts_code', 'trade_date', 'vol', 'vol_14_mean', 'condition', 'count_20d', 'alpha_pluse']])

    return pd.concat(results, ignore_index=True)


def verify_results(result_df):
    """验证结果"""
    print("\n" + "="*80)
    print("验证结果")
    print("="*80)

    # 预期结果
    expected = {
        'A': 1,  # 3天满足
        'B': 0,  # 1天满足
        'C': 0,  # 5天满足
        'D': 1,  # 2天满足
    }

    # 获取最后一天的结果
    last_date = result_df['trade_date'].max()
    last_day = result_df[result_df['trade_date'] == last_date].sort_values('ts_code')

    print(f"\n最后一天 ({last_date.strftime('%Y-%m-%d')}) 的结果:")
    print(f"{'股票':<6} {'成交量':<8} {'14日均值':<10} {'20日计数':<10} {'alpha_pluse':<12} {'预期':<6} {'状态':<6}")
    print("-" * 70)

    all_correct = True
    for ts_code in ['A', 'B', 'C', 'D']:
        row = last_day[last_day['ts_code'] == ts_code].iloc[0]
        vol = row['vol']
        mean = row['vol_14_mean']
        count = row['count_20d']
        alpha = row['alpha_pluse']
        expect = expected[ts_code]
        status = "✅" if alpha == expect else "❌"

        print(f"{ts_code:<6} {vol:<8} {mean:<10.2f} {count:<10} {alpha:<12} {expect:<6} {status:<6}")

        if alpha != expect:
            all_correct = False

    print(f"\n{'='*80}")
    if all_correct:
        print("✅ 所有验证通过！")
    else:
        print("❌ 验证失败！")
    print(f"{'='*80}")

    return all_correct


def show_detailed_example(result_df, ts_code='A'):
    """展示详细计算示例"""
    print("\n" + "="*80)
    print(f"详细计算示例 - 股票{ts_code}")
    print("="*80)

    stock = result_df[result_df['ts_code'] == ts_code].copy()
    stock = stock.sort_values('trade_date')

    # 显示最后10天
    recent = stock.tail(10)

    print(f"\n{'日期':<12} {'成交量':<8} {'14日均值':<10} {'倍数':<8} {'满足':<6} {'20日计数':<10} {'alpha':<6}")
    print("-" * 80)

    for _, row in recent.iterrows():
        date = row['trade_date'].strftime('%Y-%m-%d')
        vol = row['vol']
        mean = row['vol_14_mean']
        count = row['count_20d']
        alpha = row['alpha_pluse']

        if pd.notna(mean) and mean > 0:
            multiple = vol / mean
            condition = 1.4 <= multiple <= 3.5
            cond_str = '✓' if condition else '✗'
        else:
            multiple = 0
            cond_str = 'N/A'

        print(f"{date:<12} {vol:<8} {mean:<10.2f} {multiple:<8.2f} {cond_str:<6} {count:<10} {alpha:<6}")

    print(f"\n计算逻辑:")
    print(f"1. 每日计算前14日成交量均值")
    print(f"2. 判断当日成交量是否在1.4-3.5倍范围内")
    print(f"3. 统计20日内满足条件的天数")
    print(f"4. 如果天数∈[2,4]，则alpha_pluse=1，否则=0")


def main():
    """主函数"""
    print("\n" + "="*80)
    print("alpha_pluse因子 - 快速验证")
    print("="*80)

    # 1. 创建测试数据
    df = create_test_data()

    # 2. 手动计算演示
    manual_calculation_demo(df)

    # 3. 计算因子
    result = calculate_alpha_pluse(df)

    # 4. 验证结果
    verify_results(result)

    # 5. 展示详细示例
    show_detailed_example(result, 'A')

    # 6. 保存结果
    output_path = '/home/zcy/alpha006_20251223/results/factor/alpha_pluse_verify_result.csv'
    result.to_csv(output_path, index=False)
    print(f"\n✅ 结果已保存到: {output_path}")

    # 7. 显示完整结果
    print("\n" + "="*80)
    print("完整结果预览")
    print("="*80)
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
