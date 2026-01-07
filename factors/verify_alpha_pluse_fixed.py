"""
alpha_pluse因子 - 修正后的验证脚本

修正说明:
- 确保所有放量天数都在最后20天窗口内
- 股票A: 3天满足 -> alpha_pluse=1
- 股票B: 1天满足 -> alpha_pluse=0
- 股票C: 5天满足 -> alpha_pluse=0
- 股票D: 2天满足 -> alpha_pluse=1
"""

import pandas as pd
import numpy as np


def create_fixed_test_data():
    """创建修正后的测试数据"""
    print("\n" + "="*80)
    print("创建修正后的测试数据")
    print("="*80)

    # 生成35天数据，确保放量天数在最后20天内
    dates = pd.date_range('2025-01-01', '2025-02-04', freq='D')

    # 股票A: 最后20天内有3天满足 -> alpha_pluse=1
    vol_a = [100] * 35
    vol_a[20] = 200  # 第21天: 2倍 ✓
    vol_a[25] = 250  # 第26天: 2.5倍 ✓
    vol_a[30] = 300  # 第31天: 3倍 ✓

    # 股票B: 最后20天内有1天满足 -> alpha_pluse=0
    vol_b = [80] * 35
    vol_b[22] = 150  # 第23天: 1.875倍 ✓

    # 股票C: 最后20天内有5天满足 -> alpha_pluse=0
    vol_c = [120] * 35
    vol_c[18] = 200  # 第19天: 1.67倍 ✓
    vol_c[21] = 220  # 第22天: 1.83倍 ✓
    vol_c[24] = 250  # 第25天: 2.08倍 ✓
    vol_c[27] = 280  # 第28天: 2.33倍 ✓
    vol_c[32] = 300  # 第33天: 2.5倍 ✓

    # 股票D: 最后20天内有2天满足 -> alpha_pluse=1
    vol_d = [100] * 35
    vol_d[18] = 150  # 第19天: 1.5倍 ✓ (在20天窗口内)
    vol_d[30] = 349  # 第31天: 3.49倍 ✓ (在20天窗口内)

    data = []
    for i, date in enumerate(dates):
        data.append({'ts_code': 'A', 'trade_date': date, 'vol': vol_a[i]})
        data.append({'ts_code': 'B', 'trade_date': date, 'vol': vol_b[i]})
        data.append({'ts_code': 'C', 'trade_date': date, 'vol': vol_c[i]})
        data.append({'ts_code': 'D', 'trade_date': date, 'vol': vol_d[i]})

    df = pd.DataFrame(data)
    print(f"生成 {len(df)} 条数据，4只股票，35天")
    print(f"日期范围: {dates[0].strftime('%Y-%m-%d')} ~ {dates[-1].strftime('%Y-%m-%d')}")
    return df


def calculate_alpha_pluse(df):
    """计算alpha_pluse因子"""
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


def show_stock_detail(result_df, ts_code):
    """显示股票详细计算过程"""
    stock = result_df[result_df['ts_code'] == ts_code].copy()
    stock = stock.sort_values('trade_date')

    print(f"\n股票 {ts_code} 详细过程:")
    print(f"{'日期':<12} {'成交量':<8} {'14日均值':<10} {'倍数':<8} {'满足':<6} {'20日计数':<10} {'alpha':<6}")
    print("-" * 75)

    for _, row in stock.iterrows():
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

        mean_str = f"{mean:.2f}" if pd.notna(mean) else "N/A"
        mult_str = f"{multiple:.2f}" if multiple > 0 else "N/A"
        count_str = f"{count:.0f}" if pd.notna(count) else "N/A"
        print(f"{date:<12} {vol:<8} {mean_str:<10} {mult_str:<8} {cond_str:<6} {count_str:<10} {alpha:<6}")


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
    print(f"{'股票':<6} {'20日计数':<10} {'alpha_pluse':<12} {'预期':<6} {'状态':<6}")
    print("-" * 50)

    all_correct = True
    for ts_code in ['A', 'B', 'C', 'D']:
        row = last_day[last_day['ts_code'] == ts_code].iloc[0]
        count = row['count_20d']
        alpha = row['alpha_pluse']
        expect = expected[ts_code]
        status = "✅" if alpha == expect else "❌"

        print(f"{ts_code:<6} {count:<10} {alpha:<12} {expect:<6} {status:<6}")

        if alpha != expect:
            all_correct = False

    print(f"\n{'='*80}")
    if all_correct:
        print("✅ 所有验证通过！")
    else:
        print("❌ 验证失败！")
    print(f"{'='*80}")

    return all_correct


def main():
    """主函数"""
    print("\n" + "="*80)
    print("alpha_pluse因子 - 修正后验证")
    print("="*80)

    # 1. 创建修正后的测试数据
    df = create_fixed_test_data()

    # 2. 计算因子
    result = calculate_alpha_pluse(df)

    # 3. 显示各股票详细过程
    for stock in ['A', 'B', 'C', 'D']:
        show_stock_detail(result, stock)

    # 4. 验证结果
    verify_results(result)

    # 5. 保存结果
    output_path = '/home/zcy/alpha006_20251223/results/factor/alpha_pluse_verify_fixed.csv'
    result.to_csv(output_path, index=False)
    print(f"\n✅ 结果已保存到: {output_path}")

    # 6. 统计信息
    print("\n" + "="*80)
    print("统计信息")
    print("="*80)
    total = len(result)
    signal = result['alpha_pluse'].sum()
    print(f"总记录数: {total}")
    print(f"信号数: {signal}")
    print(f"信号比例: {signal/total:.4f}")

    # 每日统计
    daily = result.groupby('trade_date').agg({
        'alpha_pluse': ['sum', 'mean', 'count'],
        'count_20d': ['mean', 'std']
    }).round(4)
    daily.columns = ['signal_count', 'signal_ratio', 'total_stocks', 'avg_count', 'std_count']

    print(f"\n最后5天每日统计:")
    print(daily.tail(5))


if __name__ == "__main__":
    main()
