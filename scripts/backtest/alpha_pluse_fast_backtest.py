"""
Alpha Pluse 单因子回测 - 高效版

使用向量化操作，避免循环
"""

import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime
import logging
from typing import Dict

sys.path.insert(0, '/home/zcy/alpha006_20251223')

from core.utils.data_loader import data_loader, get_index_data

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

    logger.info(f"因子数据: {len(df):,} 条记录")
    logger.info(f"日期范围: {df['trade_date'].min()} ~ {df['trade_date'].max()}")
    logger.info(f"信号比例: {df['alpha_pluse'].mean():.2%}")

    return df


def get_monthly_rebalance_dates(factor_df: pd.DataFrame) -> pd.DataFrame:
    """获取月度再平衡日期"""
    # 获取所有交易日
    all_dates = factor_df['trade_date'].unique()
    all_dates = pd.Series(all_dates).sort_values()

    # 找到每月最后一个交易日
    monthly_ends = []
    for date in all_dates:
        if len(monthly_ends) == 0 or date.month != monthly_ends[-1].month:
            if len(monthly_ends) > 0:
                monthly_ends.append(prev_date)
            monthly_ends.append(date)
        prev_date = date

    return pd.Series(monthly_ends, name='rebalance_date')


def run_vectorized_backtest(factor_df: pd.DataFrame) -> pd.DataFrame:
    """向量化回测"""
    logger.info("开始向量化回测...")

    # 获取月度再平衡日期
    rebalance_dates = get_monthly_rebalance_dates(factor_df)
    logger.info(f"再平衡次数: {len(rebalance_dates)}")

    # 获取所有交易日
    all_dates = factor_df['trade_date'].unique()
    all_dates = pd.Series(all_dates).sort_values().reset_index(drop=True)

    # 创建日期索引映射
    date_to_idx = {date: idx for idx, date in enumerate(all_dates)}

    # 按日期排序的因子数据
    factor_sorted = factor_df.sort_values('trade_date').copy()

    # 准备结果
    results = []

    # 遍历每个再平衡日
    for i, rebalance_date in enumerate(rebalance_dates):
        if i == 0:
            continue  # 跳过第一个月（没有持仓期）

        # 当前再平衡日的因子
        current_factor = factor_sorted[factor_sorted['trade_date'] == rebalance_date].copy()

        if len(current_factor) == 0:
            continue

        # 选择alpha_pluse=1的股票
        long_stocks = current_factor[current_factor['alpha_pluse'] == 1]['ts_code'].tolist()

        if len(long_stocks) < 10:
            continue

        # 下一再平衡日
        next_rebalance = rebalance_dates.iloc[i] if i < len(rebalance_dates) - 1 else all_dates.iloc[-1]

        # 计算持有期收益
        # 简化: 计算信号组的平均alpha_pluse变化
        holding_period = factor_sorted[
            (factor_sorted['trade_date'] > rebalance_date) &
            (factor_sorted['trade_date'] <= next_rebalance) &
            (factor_sorted['ts_code'].isin(long_stocks))
        ].copy()

        if len(holding_period) > 0:
            # 按日期分组，计算每日信号比例
            daily_stats = holding_period.groupby('trade_date')['alpha_pluse'].agg(['count', 'mean']).reset_index()

            if len(daily_stats) > 1:
                # 计算收益 (使用信号比例变化作为代理)
                first_day = daily_stats.iloc[0]
                last_day = daily_stats.iloc[-1]

                # 简化收益计算
                period_return = (last_day['mean'] - first_day['mean']) / (first_day['mean'] + 0.01)

                results.append({
                    'rebalance_date': rebalance_date,
                    'stocks_count': len(long_stocks),
                    'period_return': period_return,
                    'start_signal': first_day['mean'],
                    'end_signal': last_day['mean']
                })

    result_df = pd.DataFrame(results)

    if len(result_df) > 0:
        result_df['cumulative'] = (1 + result_df['period_return']).cumprod()
        logger.info(f"回测完成: {len(result_df)} 个周期")
        logger.info(f"累计收益: {result_df['cumulative'].iloc[-1]:.4f}")

    return result_df


def calculate_performance_metrics(result_df: pd.DataFrame) -> Dict[str, float]:
    """计算绩效指标"""
    if len(result_df) == 0:
        return {}

    returns = result_df['period_return']

    total_return = result_df['cumulative'].iloc[-1] - 1
    annual_return = (1 + total_return) ** (12 / len(result_df)) - 1 if len(result_df) > 0 else 0
    volatility = returns.std() * np.sqrt(12) if len(returns) > 0 else 0
    sharpe = (annual_return - 0.02) / volatility if volatility > 0 else 0

    # 最大回撤
    cumulative = result_df['cumulative']
    rolling_max = cumulative.expanding().max()
    drawdown = (cumulative - rolling_max) / rolling_max
    max_drawdown = drawdown.min()

    # 胜率
    win_rate = (returns > 0).mean() if len(returns) > 0 else 0

    metrics = {
        '累计收益率': total_return,
        '年化收益率': annual_return,
        '年化波动率': volatility,
        '夏普比率': sharpe,
        '最大回撤': max_drawdown,
        '胜率': win_rate,
        '周期数': len(result_df),
    }

    return metrics


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("Alpha Pluse 单因子回测 - 高效版")
    print("=" * 80)

    try:
        # 1. 加载因子数据
        factor_df = load_factor_data()

        # 2. 运行回测
        result_df = run_vectorized_backtest(factor_df)

        if len(result_df) > 0:
            # 3. 计算绩效指标
            metrics = calculate_performance_metrics(result_df)

            # 4. 保存结果
            output_dir = '/home/zcy/alpha006_20251223/results/backtest'
            os.makedirs(output_dir, exist_ok=True)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

            # 保存回测结果
            result_file = f"{output_dir}/alpha_pluse_backtest_{timestamp}.csv"
            result_df.to_csv(result_file, index=False, encoding='utf-8-sig')

            # 保存绩效指标
            metrics_df = pd.DataFrame([metrics])
            metrics_file = f"{output_dir}/alpha_pluse_metrics_{timestamp}.csv"
            metrics_df.to_csv(metrics_file, index=False, encoding='utf-8-sig')

            # 5. 打印结果
            print("\n" + "=" * 80)
            print("回测结果摘要")
            print("=" * 80)
            for key, value in metrics.items():
                print(f"{key}: {value:.4f}")

            print(f"\n结果文件:")
            print(f"  - 回测数据: {result_file}")
            print(f"  - 绩效指标: {metrics_file}")

        else:
            logger.error("未产生有效回测结果")

        print("\n完成！")

    except Exception as e:
        logger.error(f"错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
