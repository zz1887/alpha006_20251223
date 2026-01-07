"""
文件input(依赖外部什么): factors.calculation.alpha_profit_employee, pandas
文件output(提供什么): 20250101交易日的动态截面计算示例和详细解释
文件pos(系统局部地位): 动态截面逻辑验证工具，用于教学和演示

详细说明:
1. 演示20250101交易日的动态截面筛选逻辑
2. 展示如何从数据库获取2024年Q3及之前公告的数据
3. 说明动态截面 vs 静态截面的区别

使用示例:
    python3 scripts/test/verify_20250101_example.py

返回值:
    生成详细的计算过程说明和结果对比
"""

import pandas as pd
from datetime import datetime

def demonstrate_dynamic_cross_section():
    """
    演示20250101交易日的动态截面计算逻辑
    """
    print("="*80)
    print("动态截面演示：20250101交易日")
    print("="*80)

    # 模拟数据库中的财务数据（2024年Q3及之前公告）
    print("\n1. 假设数据库中的财务数据（2024年Q3及之前公告）:")
    print("-" * 80)

    data = [
        {'ts_code': '600001.SH', 'ann_date': '20241025', 'operate_profit': 1000000000, 'c_paid_to_for_empl': 500000000, 'total_mv': 50000},
        {'ts_code': '600002.SH', 'ann_date': '20241028', 'operate_profit': 2000000000, 'c_paid_to_for_empl': 800000000, 'total_mv': 80000},
        {'ts_code': '600003.SH', 'ann_date': '20241030', 'operate_profit': 1500000000, 'c_paid_to_for_empl': 600000000, 'total_mv': 60000},
        {'ts_code': '600004.SH', 'ann_date': '20241105', 'operate_profit': 3000000000, 'c_paid_to_for_empl': 1200000000, 'total_mv': 100000},
        {'ts_code': '600005.SH', 'ann_date': '20241115', 'operate_profit': 2500000000, 'c_paid_to_for_empl': 900000000, 'total_mv': 90000},
        {'ts_code': '600006.SH', 'ann_date': '20250105', 'operate_profit': 1800000000, 'c_paid_to_for_empl': 700000000, 'total_mv': 70000},  # 2025年公告，不应被20250101看到
        {'ts_code': '600007.SH', 'ann_date': '20250110', 'operate_profit': 2200000000, 'c_paid_to_for_empl': 850000000, 'total_mv': 85000},  # 2025年公告，不应被20250101看到
    ]

    df = pd.DataFrame(data)
    print(df.to_string(index=False))

    # 交易日期
    trade_date = pd.to_datetime('20250101', format='%Y%m%d')

    print(f"\n2. 交易日期: {trade_date.strftime('%Y%m%d')}")
    print("-" * 80)

    # 动态截面筛选
    print(f"\n3. 动态截面筛选条件: ann_date ≤ {trade_date.strftime('%Y%m%d')}")
    print("-" * 80)

    df['ann_date_dt'] = pd.to_datetime(df['ann_date'], format='%Y%m%d')
    eligible_data = df[df['ann_date_dt'] <= trade_date].copy()

    print(f"筛选结果: {len(eligible_data)} 只股票（从 {len(df)} 只中筛选）")
    print("\n可用股票:")
    print(eligible_data[['ts_code', 'ann_date', 'operate_profit', 'c_paid_to_for_empl', 'total_mv']].to_string(index=False))

    # 计算原始比率
    print(f"\n4. 计算原始比率: (营业利润 + 职工现金) / (总市值 × 10000)")
    print("-" * 80)

    total_mv_yuan = eligible_data['total_mv'] * 10000
    numerator = eligible_data['operate_profit'] + eligible_data['c_paid_to_for_empl']
    ratio = numerator / total_mv_yuan

    eligible_data['factor_raw'] = ratio

    print("\n计算过程:")
    for _, row in eligible_data.iterrows():
        print(f"{row['ts_code']}: ({row['operate_profit']:,} + {row['c_paid_to_for_empl']:,}) / ({row['total_mv']*10000:,}) = {row['factor_raw']:.6f}")

    # CSRank
    print(f"\n5. 截面排名 (CSRank)")
    print("-" * 80)

    eligible_data['factor'] = eligible_data['factor_raw'].rank(pct=True, method='first')

    print("\n最终因子值:")
    result = eligible_data[['ts_code', 'ann_date', 'factor_raw', 'factor']].sort_values('factor', ascending=False)
    print(result.to_string(index=False))

    # 验证范围
    print(f"\n6. 验证结果")
    print("-" * 80)
    print(f"因子值范围: [{result['factor'].min():.4f}, {result['factor'].max():.4f}]")
    print(f"股票数量: {len(result)}")
    print(f"排名分布: {sorted(result['factor'].values)}")

    # 对比：如果使用静态截面
    print(f"\n7. 对比：静态截面（错误做法）")
    print("-" * 80)
    print("静态截面会将 ann_date=20250101 作为 trade_date")
    print("但20250101当天可能没有股票公告，或者只有少量股票")
    print("这会导致:")
    print("  - 截面样本量不稳定")
    print("  - 因子值跨日期不可比")
    print("  - 回测时可能没有股票可选")

    # 总结
    print(f"\n8. 总结")
    print("="*80)
    print("✅ 动态截面正确实现:")
    print(f"   - 20250101交易日只看到2024年Q3公告的数据")
    print(f"   - 筛选出 {len(eligible_data)} 只股票进行排名")
    print(f"   - 因子值范围: [0.2, 1.0]，符合 {len(eligible_data)} 只股票的分位数")
    print(f"   - 严格遵守 ann_date ≤ trade_date 原则")
    print("\n❌ 静态截面的问题:")
    print("   - 假设20250101当天有数据可用")
    print("   - 可能导致数据泄露")
    print("   - 截面大小不稳定")
    print("\n💡 关键理解:")
    print("   - trade_date = 您买入的日期")
    print("   - ann_date ≤ trade_date = 您能看到的数据")
    print("   - 动态截面 = 每日独立计算，只用已披露数据")

def show_data_flow():
    """
    展示完整的数据流程
    """
    print("\n\n" + "="*80)
    print("完整数据流程：从数据库到因子值")
    print("="*80)

    print("""
1. 数据库查询 (SQL)
   SELECT ts_code, ann_date, operate_profit, c_paid_to_for_empl, total_mv
   FROM income
   JOIN cashflow USING (ts_code, ann_date)
   JOIN daily_basic ON (ts_code, ann_date = trade_date)
   WHERE ann_date BETWEEN '20240101' AND '20251231'

2. 数据预处理
   - 删除空值
   - 单位转换: total_mv (万元) → 元
   - 计算原始比率: (利润+职工现金)/市值

3. 动态截面排名 (对于每个交易日)
   for trade_date in trade_dates:
       # 筛选已披露数据
       eligible = df[df['ann_date'] <= trade_date]

       # CSRank
       eligible['factor'] = eligible['factor_raw'].rank(pct=True)
       eligible['trade_date'] = trade_date

       results.append(eligible)

4. 输出结果
   ts_code    trade_date    factor
   600001.SH  20250101      0.85
   600002.SH  20250101      0.62
   ...

5. 回测使用
   20250101: 选择因子值前10%的股票买入
   20250102: 选择因子值前10%的股票买入
   ...
""")

if __name__ == "__main__":
    demonstrate_dynamic_cross_section()
    show_data_flow()

    print("\n\n" + "="*80)
    print("脚本执行完成")
    print("="*80)
    print("\n关键要点:")
    print("1. 20250101买入时，使用的是2024年Q3及之前公告的数据")
    print("2. 20250105公告的新数据，要到20250106及之后才能被看到")
    print("3. 这就是防未来函数的核心机制")
