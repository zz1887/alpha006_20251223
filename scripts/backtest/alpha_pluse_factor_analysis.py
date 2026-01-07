"""
Alpha Pluse 因子分析 - 统计和可视化

分析因子的统计特性和有效性
"""

import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns

sys.path.insert(0, '/home/zcy/alpha006_20251223')

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


def load_factor_data() -> pd.DataFrame:
    """加载因子数据"""
    cache_dir = '/home/zcy/alpha006_20251223/data/cache'
    factor_file = f"{cache_dir}/alpha_pluse_factor_20230101_20251201.csv"

    logger.info("加载因子数据...")
    df = pd.read_csv(factor_file)
    df['trade_date'] = pd.to_datetime(df['trade_date'])
    df['count_20d'] = pd.to_numeric(df['count_20d'], errors='coerce')

    logger.info(f"数据量: {len(df):,} 条")
    logger.info(f"股票数: {df['ts_code'].nunique()}")
    logger.info(f"日期数: {df['trade_date'].nunique()}")

    return df


def basic_statistics(df: pd.DataFrame) -> dict:
    """基础统计"""
    logger.info("\n" + "=" * 60)
    logger.info("基础统计")
    logger.info("=" * 60)

    stats = {
        '总记录数': len(df),
        '股票数量': df['ts_code'].nunique(),
        '交易日数': df['trade_date'].nunique(),
        '信号总数': df['alpha_pluse'].sum(),
        '信号比例': df['alpha_pluse'].mean(),
        '平均count_20d': df['count_20d'].mean(),
        'count_20d标准差': df['count_20d'].std(),
    }

    for key, value in stats.items():
        if isinstance(value, float):
            logger.info(f"{key}: {value:.4f}")
        else:
            logger.info(f"{key}: {value}")

    return stats


def signal_distribution(df: pd.DataFrame):
    """信号分布分析"""
    logger.info("\n" + "=" * 60)
    logger.info("信号分布")
    logger.info("=" * 60)

    # 按日期统计
    daily_stats = df.groupby('trade_date').agg({
        'alpha_pluse': ['sum', 'count', 'mean'],
        'count_20d': ['mean', 'std']
    }).reset_index()

    daily_stats.columns = ['trade_date', 'signal_count', 'total_count', 'signal_ratio',
                          'count_mean', 'count_std']

    logger.info(f"每日平均信号数: {daily_stats['signal_count'].mean():.0f}")
    logger.info(f"每日平均信号比例: {daily_stats['signal_ratio'].mean():.2%}")
    logger.info(f"信号比例标准差: {daily_stats['signal_ratio'].std():.4f}")

    # count_20d分布
    count_dist = df['count_20d'].value_counts().sort_index()
    logger.info(f"\ncount_20d分布:\n{count_dist}")

    return daily_stats


def time_series_analysis(df: pd.DataFrame):
    """时间序列分析"""
    logger.info("\n" + "=" * 60)
    logger.info("时间序列分析")
    logger.info("=" * 60)

    # 月度信号统计
    df['year_month'] = df['trade_date'].dt.to_period('M')
    monthly_stats = df.groupby('year_month').agg({
        'alpha_pluse': ['sum', 'count', 'mean']
    }).reset_index()

    monthly_stats.columns = ['year_month', 'signal_count', 'total_count', 'signal_ratio']

    logger.info("月度信号比例:")
    for _, row in monthly_stats.iterrows():
        logger.info(f"  {row['year_month']}: {row['signal_ratio']:.2%} ({row['signal_count']}/{row['total_count']})")

    return monthly_stats


def stock_level_analysis(df: pd.DataFrame):
    """股票层面分析"""
    logger.info("\n" + "=" * 60)
    logger.info("股票层面分析")
    logger.info("=" * 60)

    # 每只股票的信号统计
    stock_stats = df.groupby('ts_code').agg({
        'alpha_pluse': ['sum', 'count', 'mean']
    }).reset_index()

    stock_stats.columns = ['ts_code', 'signal_days', 'total_days', 'signal_ratio']

    logger.info(f"平均每只股票信号天数: {stock_stats['signal_days'].mean():.1f}")
    logger.info(f"平均每只股票信号比例: {stock_stats['signal_ratio'].mean():.2%}")

    # 信号活跃度分布
    active_bins = [0, 0.1, 0.3, 0.5, 0.7, 1.0]
    stock_stats['active_level'] = pd.cut(stock_stats['signal_ratio'], bins=active_bins)
    level_dist = stock_stats['active_level'].value_counts().sort_index()

    logger.info(f"\n股票活跃度分布:")
    for level, count in level_dist.items():
        logger.info(f"  {level}: {count} 只股票")

    return stock_stats


def generate_report(df: pd.DataFrame):
    """生成完整报告"""
    output_dir = '/home/zcy/alpha006_20251223/results/backtest'
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # 1. 基础统计报告
    stats = basic_statistics(df)
    stats_df = pd.DataFrame([stats])
    stats_file = f"{output_dir}/alpha_pluse_basic_stats_{timestamp}.csv"
    stats_df.to_csv(stats_file, index=False, encoding='utf-8-sig')
    logger.info(f"\n基础统计已保存: {stats_file}")

    # 2. 信号分布
    daily_stats = signal_distribution(df)
    daily_file = f"{output_dir}/alpha_pluse_daily_stats_{timestamp}.csv"
    daily_stats.to_csv(daily_file, index=False, encoding='utf-8-sig')
    logger.info(f"每日统计已保存: {daily_file}")

    # 3. 月度统计
    monthly_stats = time_series_analysis(df)
    monthly_file = f"{output_dir}/alpha_pluse_monthly_stats_{timestamp}.csv"
    monthly_stats.to_csv(monthly_file, index=False, encoding='utf-8-sig')
    logger.info(f"月度统计已保存: {monthly_file}")

    # 4. 股票统计
    stock_stats = stock_level_analysis(df)
    stock_file = f"{output_dir}/alpha_pluse_stock_stats_{timestamp}.csv"
    stock_stats.to_csv(stock_file, index=False, encoding='utf-8-sig')
    logger.info(f"股票统计已保存: {stock_file}")

    # 5. 生成可视化图表
    try:
        generate_visualizations(daily_stats, monthly_stats, stock_stats, output_dir, timestamp)
    except Exception as e:
        logger.warning(f"可视化生成失败: {e}")

    logger.info("\n" + "=" * 80)
    logger.info("分析完成！")
    logger.info("=" * 80)


def generate_visualizations(daily_stats, monthly_stats, stock_stats, output_dir, timestamp):
    """生成可视化图表"""
    plt.style.use('default')
    sns.set_palette("husl")

    # 1. 每日信号比例时间序列
    plt.figure(figsize=(12, 6))
    plt.plot(daily_stats['trade_date'], daily_stats['signal_ratio'], linewidth=1)
    plt.title('Alpha Pluse 信号比例时间序列')
    plt.xlabel('日期')
    plt.ylabel('信号比例')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"{output_dir}/alpha_pluse_signal_ratio_{timestamp}.png", dpi=150)
    plt.close()

    # 2. 月度信号比例
    plt.figure(figsize=(12, 6))
    months = [str(m) for m in monthly_stats['year_month']]
    plt.bar(months, monthly_stats['signal_ratio'])
    plt.title('Alpha Pluse 月度信号比例')
    plt.xlabel('月份')
    plt.ylabel('信号比例')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f"{output_dir}/alpha_pluse_monthly_ratio_{timestamp}.png", dpi=150)
    plt.close()

    # 3. Count_20d分布
    if 'count_20d' in daily_stats.columns:
        plt.figure(figsize=(10, 6))
        plt.plot(daily_stats['trade_date'], daily_stats['count_mean'], label='均值')
        plt.fill_between(daily_stats['trade_date'],
                        daily_stats['count_mean'] - daily_stats['count_std'],
                        daily_stats['count_mean'] + daily_stats['count_std'],
                        alpha=0.3, label='±1σ')
        plt.title('Count_20d 时间序列')
        plt.xlabel('日期')
        plt.ylabel('Count_20d')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(f"{output_dir}/alpha_pluse_count_20d_{timestamp}.png", dpi=150)
        plt.close()

    # 4. 股票活跃度分布
    plt.figure(figsize=(10, 6))
    signal_ratios = stock_stats['signal_ratio']
    plt.hist(signal_ratios, bins=30, edgecolor='black', alpha=0.7)
    plt.title('股票信号比例分布')
    plt.xlabel('信号比例')
    plt.ylabel('股票数量')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"{output_dir}/alpha_pluse_stock_dist_{timestamp}.png", dpi=150)
    plt.close()

    logger.info(f"可视化图表已保存到: {output_dir}")


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("Alpha Pluse 因子统计分析")
    print("=" * 80)

    try:
        # 加载数据
        df = load_factor_data()

        # 生成报告
        generate_report(df)

        print("\n所有分析完成！请查看 results/backtest/ 目录下的结果文件")

    except Exception as e:
        logger.error(f"分析失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
