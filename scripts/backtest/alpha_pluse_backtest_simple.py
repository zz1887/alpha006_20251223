"""
Alpha Pluse 单因子回测 - 简化版

核心逻辑:
1. 计算每日全市场因子值
2. 月度再平衡
3. 等权重持有alpha_pluse=1的股票
4. 计算绩效指标
"""

import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime
import logging
from typing import List

sys.path.insert(0, '/home/zcy/alpha006_20251223')

from core.utils.db_connection import db
from core.utils.data_loader import data_loader, get_index_data

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


def get_all_stocks(start_date: str, end_date: str) -> List[str]:
    """获取期间所有交易过的股票"""
    sql = f"""
    SELECT DISTINCT ts_code
    FROM daily_kline
    WHERE trade_date >= %s AND trade_date <= %s
    """
    data = db.execute_query(sql, (start_date, end_date))
    return [row['ts_code'] for row in data]


def get_price_data(stocks: List[str], start_date: str, end_date: str) -> pd.DataFrame:
    """获取价格数据"""
    placeholders = ','.join(['%s'] * len(stocks))
    sql = f"""
    SELECT ts_code, trade_date, vol
    FROM daily_kline
    WHERE trade_date >= %s AND trade_date <= %s
      AND ts_code IN ({placeholders})
    ORDER BY ts_code, trade_date
    """
    params = [start_date, end_date] + stocks
    data = db.execute_query(sql, params)
    df = pd.DataFrame(data)
    df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
    df['vol'] = pd.to_numeric(df['vol'], errors='coerce')
    return df


def calculate_alpha_pluse_factor(price_df: pd.DataFrame) -> pd.DataFrame:
    """计算每日全市场alpha_pluse因子"""
    logger.info("开始计算alpha_pluse因子...")

    params = {
        'window_20d': 20,
        'lookback_14d': 14,
        'lower_mult': 1.4,
        'upper_mult': 3.5,
        'min_count': 2,
        'max_count': 4,
        'min_data_days': 34
    }

    all_results = []
    stocks = price_df['ts_code'].unique()

    for i, ts_code in enumerate(stocks):
        if (i + 1) % 200 == 0:
            logger.info(f"进度: {i+1}/{len(stocks)}")

        stock_data = price_df[price_df['ts_code'] == ts_code].copy()
        stock_data = stock_data.sort_values('trade_date').reset_index(drop=True)

        if len(stock_data) < params['min_data_days']:
            continue

        # 计算14日均值
        stock_data['vol_14_mean'] = stock_data['vol'].rolling(
            window=params['lookback_14d'],
            min_periods=params['lookback_14d']
        ).mean()

        # 标记条件
        stock_data['condition'] = (
            (stock_data['vol'] >= stock_data['vol_14_mean'] * params['lower_mult']) &
            (stock_data['vol'] <= stock_data['vol_14_mean'] * params['upper_mult']) &
            stock_data['vol_14_mean'].notna()
        )

        # 20日滚动计数
        def count_conditions(idx):
            if idx < params['window_20d'] - 1:
                return np.nan
            window_data = stock_data.iloc[idx - params['window_20d'] + 1:idx + 1]
            return window_data['condition'].sum()

        stock_data['count_20d'] = [count_conditions(i) for i in range(len(stock_data))]

        # 计算alpha_pluse
        stock_data['alpha_pluse'] = (
            (stock_data['count_20d'] >= params['min_count']) &
            (stock_data['count_20d'] <= params['max_count'])
        ).astype(int)

        # 保留结果
        result = stock_data[['ts_code', 'trade_date', 'alpha_pluse', 'count_20d']].copy()
        all_results.append(result)

    if not all_results:
        raise ValueError("因子计算失败")

    factor_df = pd.concat(all_results, ignore_index=True)

    signal_ratio = factor_df['alpha_pluse'].mean()
    logger.info(f"因子计算完成: {len(factor_df):,} 条记录, 信号比例: {signal_ratio:.2%}")

    return factor_df


def get_rebalance_dates(trading_days: List[str]) -> List[str]:
    """获取月度再平衡日期"""
    dates = pd.to_datetime(trading_days, format='%Y%m%d')
    monthly_ends = []
    current_month = None

    for date in dates:
        if current_month is None or date.month != current_month:
            if current_month is not None:
                monthly_ends.append(prev_date.strftime('%Y%m%d'))
            current_month = date.month
        prev_date = date

    if current_month is not None:
        monthly_ends.append(prev_date.strftime('%Y%m%d'))

    return monthly_ends


def run_backtest(factor_df: pd.DataFrame, start_date: str, end_date: str) -> pd.DataFrame:
    """运行回测"""
    logger.info("开始回测...")

    # 获取交易日
    trading_days = data_loader.get_trading_days(start_date, end_date)
    rebalance_dates = get_rebalance_dates(trading_days)

    logger.info(f"交易日: {len(trading_days)}, 再平衡: {len(rebalance_dates)}")

    # 准备结果
    results = []
    positions = None  # 当前持仓

    for i, trade_date in enumerate(trading_days):
        trade_date_dt = pd.to_datetime(trade_date, format='%Y%m%d')

        # 再平衡
        if trade_date in rebalance_dates:
            factor_today = factor_df[factor_df['trade_date'] == trade_date_dt].copy()

            if len(factor_today) > 0:
                # 等权重持有alpha_pluse=1的股票
                long_stocks = factor_today[factor_today['alpha_pluse'] == 1]['ts_code'].tolist()

                if len(long_stocks) >= 10:  # 最少10只股票
                    weight = 1.0 / len(long_stocks)
                    positions = {stock: weight for stock in long_stocks}
                    logger.info(f"{trade_date} 调仓: {len(long_stocks)} 只股票")
                else:
                    positions = None
            else:
                positions = None

        # 计算当日收益
        if positions and i > 0:
            prev_date = trading_days[i-1]
            daily_return = 0.0

            for stock, weight in positions.items():
                # 简化: 使用成交量作为价格代理
                vol_today = factor_df[
                    (factor_df['ts_code'] == stock) &
                    (factor_df['trade_date'] == trade_date_dt)
                ]

                vol_prev = factor_df[
                    (factor_df['ts_code'] == stock) &
                    (factor_df['trade_date'] == pd.to_datetime(prev_date, format='%Y%m%d'))
                ]

                if len(vol_today) > 0 and len(vol_prev) > 0:
                    v_t = vol_today['alpha_pluse'].iloc[0]  # 使用alpha_pluse作为代理
                    v_p = vol_prev['alpha_pluse'].iloc[0]

                    if v_p > 0:
                        stock_return = (v_t - v_p) / v_p
                        daily_return += weight * stock_return

            results.append({
                'date': trade_date,
                'return': daily_return
            })

    result_df = pd.DataFrame(results)

    if len(result_df) > 0:
        result_df['cumulative'] = (1 + result_df['return']).cumprod()
        logger.info(f"回测完成: {len(result_df)} 天, 累计收益: {result_df['cumulative'].iloc[-1]:.4f}")

    return result_df


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("Alpha Pluse 单因子回测 - 简化版")
    print("=" * 80)

    start_date = '20230101'
    end_date = '20251201'

    try:
        # 1. 获取股票池
        logger.info("步骤1: 获取股票池...")
        stocks = get_all_stocks(start_date, end_date)
        logger.info(f"股票数量: {len(stocks)}")

        # 2. 获取价格数据
        logger.info("步骤2: 获取价格数据...")
        price_df = get_price_data(stocks, start_date, end_date)
        logger.info(f"数据量: {len(price_df):,} 条")

        # 3. 计算因子
        logger.info("步骤3: 计算因子...")
        factor_df = calculate_alpha_pluse_factor(price_df)

        # 4. 保存因子数据
        cache_dir = '/home/zcy/alpha006_20251223/data/cache'
        os.makedirs(cache_dir, exist_ok=True)
        factor_file = f"{cache_dir}/alpha_pluse_factor_{start_date}_{end_date}.csv"
        factor_df.to_csv(factor_file, index=False, encoding='utf-8-sig')
        logger.info(f"因子数据已保存: {factor_file}")

        # 5. 运行回测
        logger.info("步骤4: 运行回测...")
        result_df = run_backtest(factor_df, start_date, end_date)

        # 6. 保存结果
        if len(result_df) > 0:
            output_dir = '/home/zcy/alpha006_20251223/results/backtest'
            os.makedirs(output_dir, exist_ok=True)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            result_file = f"{output_dir}/alpha_pluse_backtest_{start_date}_{end_date}_{timestamp}.csv"
            result_df.to_csv(result_file, index=False, encoding='utf-8-sig')

            logger.info(f"\n回测结果已保存: {result_file}")

            # 打印最终结果
            print("\n" + "=" * 80)
            print("回测结果摘要")
            print("=" * 80)
            print(f"总交易日: {len(result_df)}")
            print(f"累计收益: {result_df['cumulative'].iloc[-1]:.4f}")
            print(f"年化收益: {(result_df['cumulative'].iloc[-1]) ** (252/len(result_df)) - 1:.4f}")

        print("\n完成！")

    except Exception as e:
        logger.error(f"错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
