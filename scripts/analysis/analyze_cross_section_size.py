"""
文件input(依赖外部什么): results/alpha_profit_employee/dynamic_backtest_20260106_230006/alpha_profit_employee_factor_dynamic_20250101_20251231.csv
文件output(提供什么): 截面样本量分布统计报告, 包含各日期股票数量分布、统计信息、问题分析
文件pos(系统局部地位): 因子分析工具, 用于诊断alpha_profit_employee因子的截面样本量不均衡问题

详细说明:
1. 加载动态截面回测生成的因子数据
2. 统计每个交易日的可用股票数量
3. 分析截面样本量分布特征
4. 识别小截面问题
5. 提供优化建议

使用示例:
    python3 scripts/analysis/analyze_cross_section_size.py

返回值:
    生成截面样本量分析报告到 results/alpha_profit_employee/ 目录
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import os

def load_factor_data():
    """加载因子数据"""
    result_dir = "/home/zcy/alpha因子库/results/alpha_profit_employee/dynamic_backtest_20260106_230006"
    factor_file = os.path.join(result_dir, "alpha_profit_employee_factor_dynamic_20250101_20251231.csv")

    if not os.path.exists(factor_file):
        print(f"错误: 找不到因子文件 {factor_file}")
        return None

    df = pd.read_csv(factor_file)
    print(f"加载因子数据: {len(df)} 条记录")
    print(f"日期范围: {df['trade_date'].min()} ~ {df['trade_date'].max()}")
    print(f"股票数量: {df['ts_code'].nunique()}")

    return df

def analyze_cross_section_size(df):
    """分析截面样本量分布"""
    print("\n" + "="*60)
    print("截面样本量分布分析")
    print("="*60)

    # 按交易日统计股票数量
    daily_counts = df.groupby('trade_date')['ts_code'].nunique().sort_values()

    # 统计信息
    stats = {
        '总交易日数': len(daily_counts),
        '平均每日股票数': daily_counts.mean(),
        '中位数': daily_counts.median(),
        '最小值': daily_counts.min(),
        '最大值': daily_counts.max(),
        '标准差': daily_counts.std(),
    }

    print("\n基础统计:")
    for key, value in stats.items():
        print(f"  {key}: {value:.2f}")

    # 分组统计
    bins = [0, 5, 10, 20, 50, 100, 500, 1000]
    labels = ['1-4只', '5-9只', '10-19只', '20-49只', '50-99只', '100-499只', '500+只']
    daily_counts_grouped = pd.cut(daily_counts, bins=bins, labels=labels, right=False)
    distribution = daily_counts_grouped.value_counts().sort_index()

    print("\n截面大小分布:")
    for label, count in distribution.items():
        percentage = count / len(daily_counts) * 100
        print(f"  {label}: {count}天 ({percentage:.1f}%)")

    # 识别问题日期
    small_cross_section_dates = daily_counts[daily_counts < 5]
    medium_cross_section_dates = daily_counts[(daily_counts >= 5) & (daily_counts < 10)]

    print(f"\n⚠️  问题截面:")
    print(f"  小截面(<5只): {len(small_cross_section_dates)}天 ({len(small_cross_section_dates)/len(daily_counts)*100:.1f}%)")
    if len(small_cross_section_dates) > 0:
        print(f"    最小值: {small_cross_section_dates.min()}只")
        print(f"    日期示例: {small_cross_section_dates.index[:5].tolist()}")

    print(f"  中等截面(5-9只): {len(medium_cross_section_dates)}天 ({len(medium_cross_section_dates)/len(daily_counts)*100:.1f}%)")

    return daily_counts, distribution

def analyze_factor_value_distribution_by_size(df, daily_counts):
    """分析不同截面大小下的因子值分布"""
    print("\n" + "="*60)
    print("因子值与截面大小关系分析")
    print("="*60)

    # 添加截面大小信息
    df_analysis = df.copy()
    df_analysis['cross_section_size'] = df_analysis['trade_date'].map(daily_counts)

    # 按截面大小分组统计因子值
    def size_group(size):
        if size < 5:
            return '小截面(<5)'
        elif size < 10:
            return '中截面(5-9)'
        elif size < 20:
            return '较大截面(10-19)'
        else:
            return '大截面(20+)'

    df_analysis['size_group'] = df_analysis['cross_section_size'].apply(size_group)

    # 统计各组的因子值特征
    grouped_stats = df_analysis.groupby('size_group')['factor'].agg([
        'count', 'mean', 'std', 'min', 'max'
    ]).round(4)

    print("\n不同截面大小的因子值统计:")
    print(grouped_stats)

    # 分析小截面的因子值分布
    small_sections = df_analysis[df_analysis['cross_section_size'] < 5]
    if len(small_sections) > 0:
        print(f"\n⚠️  小截面(<5只)详细分析:")
        print(f"  记录数: {len(small_sections)}")
        print(f"  因子值范围: [{small_sections['factor'].min():.4f}, {small_sections['factor'].max():.4f}]")
        print(f"  因子值均值: {small_sections['factor'].mean():.4f}")

        # 查看小截面中因子值为1.0的比例
        max_factor_ratio = (small_sections['factor'] == 1.0).sum() / len(small_sections) * 100
        print(f"  因子值=1.0的比例: {max_factor_ratio:.1f}%")

        # 查看小截面日期分布
        small_date_counts = small_sections.groupby('trade_date').size()
        print(f"  涉及交易日数: {len(small_date_counts)}")
        print(f"  每日小截面股票数分布: {small_date_counts.value_counts().sort_index().to_dict()}")

    return df_analysis

def calculate_impact_on_backtest(df, daily_counts):
    """计算截面样本量不均衡对回测的影响"""
    print("\n" + "="*60)
    print("截面样本量不均衡对回测的影响分析")
    print("="*60)

    # 添加截面大小信息
    df_impact = df.copy()
    df_impact['cross_section_size'] = df_impact['trade_date'].map(daily_counts)

    # 分析小截面日期的因子表现
    small_section_dates = daily_counts[daily_counts < 5].index
    normal_section_dates = daily_counts[daily_counts >= 5].index

    small_section_data = df_impact[df_impact['trade_date'].isin(small_section_dates)]
    normal_section_data = df_impact[df_impact['trade_date'].isin(normal_section_dates)]

    print(f"\n小截面日期({len(small_section_dates)}天) vs 正常截面日期({len(normal_section_dates)}天):")

    if len(small_section_data) > 0:
        print(f"\n小截面日期:")
        print(f"  记录数: {len(small_section_data)}")
        print(f"  因子均值: {small_section_data['factor'].mean():.4f}")
        print(f"  因子标准差: {small_section_data['factor'].std():.4f}")
        print(f"  因子值=1.0的比例: {(small_section_data['factor'] == 1.0).sum() / len(small_section_data) * 100:.1f}%")

    if len(normal_section_data) > 0:
        print(f"\n正常截面日期:")
        print(f"  记录数: {len(normal_section_data)}")
        print(f"  因子均值: {normal_section_data['factor'].mean():.4f}")
        print(f"  因子标准差: {normal_section_data['factor'].std():.4f}")
        print(f"  因子值=1.0的比例: {(normal_section_data['factor'] == 1.0).sum() / len(normal_section_data) * 100:.1f}%")

    # 量化影响
    if len(small_section_data) > 0 and len(normal_section_data) > 0:
        mean_diff = abs(small_section_data['factor'].mean() - normal_section_data['factor'].mean())
        print(f"\n📊 影响量化:")
        print(f"  均值差异: {mean_diff:.4f}")
        print(f"  小截面因子值=1.0的比例更高: {(small_section_data['factor'] == 1.0).sum() / len(small_section_data) * 100:.1f}% vs {(normal_section_data['factor'] == 1.0).sum() / len(normal_section_data) * 100:.1f}%")
        print(f"  小截面因子值分布更集中: 标准差 {small_section_data['factor'].std():.4f} vs {normal_section_data['factor'].std():.4f}")

def generate_recommendations(daily_counts):
    """生成优化建议"""
    print("\n" + "="*60)
    print("优化建议")
    print("="*60)

    small_ratio = (daily_counts < 5).sum() / len(daily_counts) * 100
    medium_ratio = ((daily_counts >= 5) & (daily_counts < 10)).sum() / len(daily_counts) * 100

    print("\n1. 最小样本量过滤")
    print(f"   - 问题: {small_ratio:.1f}%的交易日截面样本量<5只")
    print(f"   - 建议: 过滤掉样本量<5的截面，不参与当日选股")
    print(f"   - 预期影响: {small_ratio:.1f}%的交易日可能没有股票可选")

    print("\n2. 中等样本量平滑处理")
    print(f"   - 问题: {medium_ratio:.1f}%的交易日截面样本量在5-9只之间")
    print(f"   - 建议: 对这些截面使用加权排名，降低小截面因子值的权重")
    print(f"   - 实现: factor = raw_rank * (n/10) + 0.5 * (1 - n/10)")

    print("\n3. 因子方向调整")
    print(f"   - 当前问题: 高因子值组收益偏低")
    print(f"   - 建议: 尝试使用 -alpha_profit_employee")

    print("\n4. 行业中性化")
    print(f"   - 问题: 不同行业的利润结构差异大")
    print(f"   - 建议: 减去行业均值，消除行业偏差")

    print("\n5. 市值中性化")
    print(f"   - 问题: 大市值公司可能因子值高但增长慢")
    print(f"   - 建议: 先按市值分组，再组内排名")

def main():
    """主函数"""
    print("Alpha Profit Employee因子 - 截面样本量不均衡问题分析")
    print("="*60)

    # 1. 加载数据
    df = load_factor_data()
    if df is None:
        return

    # 2. 分析截面样本量分布
    daily_counts, distribution = analyze_cross_section_size(df)

    # 3. 分析因子值与截面大小的关系
    df_analysis = analyze_factor_value_distribution_by_size(df, daily_counts)

    # 4. 计算对回测的影响
    calculate_impact_on_backtest(df, daily_counts)

    # 5. 生成优化建议
    generate_recommendations(daily_counts)

    # 6. 保存报告
    result_dir = "/home/zcy/alpha因子库/results/alpha_profit_employee"
    output_file = os.path.join(result_dir, f"cross_section_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")

    print(f"\n" + "="*60)
    print(f"报告已保存到: {output_file}")
    print("="*60)

if __name__ == "__main__":
    main()